"""Small local Markdown renderer with keyboard accessible topic navigation."""
import re
import webbrowser
from .appearance import PALETTES


def render(app):
    from .app import resource_root
    topic=next(p for p in app.help_topics if p['title']==app.help_topic.get())
    source=(resource_root()/'docs/help'/topic['path']).read_text(encoding='utf-8')
    view=app.help_text;view.configure(state='normal');view.delete('1.0','end')
    p=PALETTES[app.theme.get()]
    size=app.settings.text_size
    for level in (1,2,3):
        view.tag_configure('heading'+str(level),font=('Segoe UI',size+5-level,'bold'),spacing1=12,spacing3=6)
    view.tag_configure('code',font=('Consolas',size),background=p['field'])
    in_code=False;links=0
    for line in source.splitlines():
        if line.startswith('```'):
            in_code=not in_code;continue
        heading=re.match(r'^(#{1,3})\s+(.*)',line)
        tag='heading'+str(len(heading[1])) if heading else 'code' if in_code else ''
        text=heading[2] if heading else line
        cursor=0
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)',text):
            view.insert('end',re.sub(r'\*\*|`','',text[cursor:match.start()]),tag)
            start=view.index('end-1c');link='topic_link_'+str(links);links+=1
            view.insert('end',match[1],(tag,link))
            view.tag_configure(link,foreground=p['accent'],underline=True)
            target=match[2]
            def open_link(event=None,destination=target):
                if destination.startswith('https://'):webbrowser.open(destination);return
                name=destination.split('#')[0].split('/')[-1]
                local=next((page for page in app.help_topics if page['path']==name),None)
                if local:app.help_topic.set(local['title']);app._show_help()
            view.tag_bind(link,'<Button-1>',open_link)
            cursor=match.end()
        view.insert('end',re.sub(r'\*\*|`','',text[cursor:])+'\n',tag)
    # Plain web URLs remain usable as well as Markdown links.
    text=view.get('1.0','end-1c')
    for index,match in enumerate(re.finditer(r'https://[^\s)]+',text)):
        tag='web_link_'+str(index);url=match.group()
        view.tag_add(tag,f'1.0+{match.start()}c',f'1.0+{match.end()}c')
        view.tag_configure(tag,foreground=p['accent'],underline=True)
        view.tag_bind(tag,'<Button-1>',lambda event,link=url:webbrowser.open(link))
    view.configure(state='disabled')
