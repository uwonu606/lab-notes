import re, sys
# jieba/__init__.py (fxsjy/jieba 67fa2e3) lines 44, 46 and Tokenizer.cut non-Han branch, copied as regex only
re_han = re.compile("([一-鿕a-zA-Z0-9+#&\\._%\\-]+)", re.U)
re_skip = re.compile("(\r\n|\\s)", re.U)
def cut_non_han_branch(sentence):
    for blk in re_han.split(sentence):
        if not blk:
            continue
        if re_han.match(blk):
            yield blk  # Han/ASCII block: real jieba runs DAG here; ASCII runs stay whole
        else:
            for x in re_skip.split(blk):
                if re_skip.match(x):
                    yield x
                else:
                    for xx in x:
                        yield xx
for s in sys.argv[1:]:
    terms = [t for t in (w.strip() for w in cut_non_han_branch(s)) if t and t.isalnum()]
    print(repr(s), '->', ' OR '.join('"%s"' % t for t in terms))
