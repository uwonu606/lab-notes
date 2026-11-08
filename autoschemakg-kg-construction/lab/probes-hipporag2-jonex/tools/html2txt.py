import sys, html.parser, re
class P(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t=='math' and not s.skip: s.out.append(' '+dict(a).get('alttext','')+' ')
        if t in ('script','style','math'): s.skip+=1
        if t in ('p','div','tr','h1','h2','h3','h4','li','br','table','figcaption'): s.out.append('\n')
        if t in ('td','th'): s.out.append(' | ')
    def handle_endtag(s,t):
        if t in ('script','style','math'): s.skip-=1
    def handle_startendtag(s,t,a):
        if t=='math':
            pass
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
src,dst=sys.argv[1],sys.argv[2]
p=P(); p.feed(open(src,encoding='utf-8',errors='ignore').read())
t=''.join(p.out); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(dst,'w').write(t)
