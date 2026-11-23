"""Show the listening transfer as readable QR pages."""
import base64
import io
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from . import transfer


def show_listening_qr(app, settings):
    document = transfer.listening_document(settings)
    pages = transfer.qr_sequence(document)
    window = tk.Toplevel(app.root)
    window.title('Send listening settings to Android')
    window.transient(app.root)
    window.bind('<Escape>', lambda event: window.destroy())
    viewer = ttk.Frame(window, padding=16)
    viewer.pack()
    caption = tk.StringVar()
    ttk.Label(viewer, textvariable=caption).pack()
    picture = ttk.Label(viewer)
    picture.pack(pady=10)
    controls = ttk.Frame(viewer)
    controls.pack()
    position = 0

    def show(index):
        nonlocal position
        import qrcode
        from qrcode.image.pure import PyPNGImage

        output = io.BytesIO()
        code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
        code.add_data(pages[index])
        code.make(fit=True)
        code.box_size = max(2, min(4, (window.winfo_screenheight()-210)//(code.modules_count+8)))
        code.make_image(image_factory=PyPNGImage).save(output)
        photo = tk.PhotoImage(data=base64.b64encode(output.getvalue()))
        picture.configure(image=photo)
        picture.image = photo
        position = index
        caption.set(f'Listening settings and saved presets. QR {index+1} of {len(pages)}')
        previous.configure(state='normal' if index else 'disabled')
        following.configure(state='normal' if index+1 < len(pages) else 'disabled')

    def save_file():
        path = filedialog.asksaveasfilename(parent=window, title='Save listening settings',
                                            defaultextension='.dxt.json',
                                            filetypes=[('DX Talker transfer', '*.json')])
        if path:
            Path(path).write_bytes(transfer.encode(document))

    previous = ttk.Button(controls, text='Previous', command=lambda: show(position-1))
    previous.pack(side='left', padx=8)
    following = ttk.Button(controls, text='Next', command=lambda: show(position+1))
    following.pack(side='left', padx=8)
    ttk.Button(controls, text='Save transfer file', command=app.guard(save_file)).pack(side='left', padx=8)
    ttk.Label(viewer, text='In Android Filters, choose Scan listening QR. Scan every page to review and import the collection together.',
              wraplength=540).pack(pady=(10, 0))
    show(0)
