"""Plain-text extracts of the main paper and Online Resource 1 for word counting.
Excludes references, figures, tables, algorithms and display equations; citations and cross-references count as one word each, inline maths as one word."""
import re, subprocess, sys
def clean(src):
    s = open(src, encoding="utf-8").read()
    s = re.sub(r"(?<!\\)%.*", "", s)
    s = s.split("\\begin{document}", 1)[-1]
    s = re.split(r"\\bibliography\{|\\begin\{thebibliography\}", s)[0]
    for env in ("figure*", "figure", "table*", "table", "algorithm", "equation*", "equation", "align*", "align", "tikzpicture", "minipage"):
        s = re.sub(r"\\begin\{%s\}.*?\\end\{%s\}" % (re.escape(env), re.escape(env)), " ", s, flags=re.S)
    s = re.sub(r"\\\[.*?\\\]", " ", s, flags=re.S)
    s = re.sub(r"\\(?:eq)?cite[a-z]*(?:\[[^\]]*\])*\{[^}]*\}", "[1]", s)
    s = re.sub(r"\\(?:eq)?ref\{[^}]*\}", "1", s)
    s = re.sub(r"\\(?:label|hypersetup|setcounter|bibliographystyle)(\{[^{}]*(\{[^{}]*\})?[^{}]*\})+", " ", s)
    s = re.sub(r"\\hypersetup\{.*?\}\n\n", " ", s, flags=re.S)
    s = re.sub(r"\\title\[[^\]]*\]", r"\\title", s)
    s = re.sub(r"\$[^$]*\$", " M ", s)
    open("/tmp/wc_in.tex", "w").write(s)
    out = subprocess.run(["detex", "-n", "/tmp/wc_in.tex"], capture_output=True, text=True).stdout
    out = out.replace("~", " ").replace("{,}", ",")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", out)).strip() + "\n"
for src, dst in (("main.tex", "wordcount/main_words.txt"), ("supplementary.tex", "wordcount/OR1_words.txt")):
    t = clean(src); open(dst, "w").write(t); print(dst, len(t.split()), "words")
