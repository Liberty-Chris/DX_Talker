"""Collection selection and readable QR pages. No credentials enter this view."""
import base64
import io
import tkinter as tk
from tkinter import ttk
from . import transfer


def show_profile_qr(app):
    profiles = app.profile_store.profiles if app.profile_store else []
    if not profiles:
        raise ValueError('Save a cluster profile first')
    window = tk.Toplevel(app.root)
    window.title('Send profiles to Android')
    window.transient(app.root)
    panel = ttk.Frame(window, padding=16)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Choose profiles. Your entire collection is selected.').pack(anchor='w')
    choices = ttk.Frame(panel)
    choices.pack(fill='both', expand=True, pady=8)
    selection = tk.Listbox(choices, selectmode='extended', exportselection=False, width=60, height=min(10, len(profiles)))
    scrollbar = ttk.Scrollbar(choices, orient='vertical', command=selection.yview)
    selection.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    selection.pack(side='left', fill='both', expand=True)
    for profile in profiles:
        selection.insert('end', profile['name'])
    selection.selection_set(0, 'end')
    actions = ttk.Frame(panel)
    actions.pack(fill='x')
    ttk.Button(actions, text='Select all', command=lambda: selection.selection_set(0, 'end')).pack(side='left')
    ttk.Button(actions, text='Clear selection', command=lambda: selection.selection_clear(0, 'end')).pack(side='left', padx=8)
    ttk.Label(panel, text='Saved connections and current filters only. Passwords and tokens stay on this PC.', wraplength=530).pack(anchor='w', pady=8)

    def generate():
        chosen = [profiles[i] for i in selection.curselection()]
        if not chosen:
            raise ValueError('Choose at least one profile')
        pages = transfer.qr_sequence(transfer.document(chosen, app._read_settings()))
        panel.pack_forget()
        viewer = ttk.Frame(window, padding=16)
        viewer.pack()
        caption = tk.StringVar()
        ttk.Label(viewer, textvariable=caption).pack()
        picture = ttk.Label(viewer)
        picture.pack(pady=10)
        controls = ttk.Frame(viewer)
        controls.pack()
        position = [0]

        def show(index):
            import qrcode
            from qrcode.image.pure import PyPNGImage
            position[0] = index
            output = io.BytesIO()
            code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
            code.add_data(pages[index])
            code.make(fit=True)
            code.box_size = max(2, min(4, (window.winfo_screenheight()-210)//(code.modules_count+8)))
            code.make_image(image_factory=PyPNGImage).save(output)
            photo = tk.PhotoImage(data=base64.b64encode(output.getvalue()))
            picture.configure(image=photo)
            picture.image = photo
            caption.set(f'{len(chosen)} profiles. QR {index+1} of {len(pages)}')
            previous.configure(state='normal' if index else 'disabled')
            following.configure(state='normal' if index+1 < len(pages) else 'disabled')

        previous = ttk.Button(controls, text='Previous', command=lambda: show(position[0]-1))
        previous.pack(side='left', padx=8)
        following = ttk.Button(controls, text='Next', command=lambda: show(position[0]+1))
        following.pack(side='left', padx=8)
        def choose_again():
            viewer.destroy()
            panel.pack(fill='both', expand=True)
        ttk.Button(controls, text='Choose profiles', command=choose_again).pack(side='left', padx=8)
        ttk.Label(viewer, text='In Android choose Scan desktop QR. Scan every page in any order, then review the complete collection before importing. Update Android first for multiple QR pages.', wraplength=540).pack(pady=(10,0))
        show(0)
    ttk.Button(actions, text='Generate QR codes', command=app.guard(generate)).pack(side='right')
