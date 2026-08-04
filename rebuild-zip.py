import os, zipfile
os.chdir(r'C:\Users\respe\qmm-racing')
if os.path.exists('qmm-racing-itch.zip'):
    os.remove('qmm-racing-itch.zip')
with zipfile.ZipFile('qmm-racing-itch.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('index.html', 'index.html')
    z.write('README.md', 'README.md')
    for root, dirs, files in os.walk('assets'):
        for f in files:
            fp = os.path.join(root, f)
            arc = fp.replace(os.sep, '/')
            z.write(fp, arc)
print('rebuilt')
with zipfile.ZipFile('qmm-racing-itch.zip') as z:
    names = z.namelist()
    print('total:', len(names))
    print('index at root:', 'index.html' in names)
    bs = [n for n in names if '\\' in n]
    print('backslash entries:', len(bs))
    print('sample:', names[0], '|', names[len(names)//2], '|', names[-1])
