from pdfminer.high_level import extract_text
p=r'c:\\Users\\Alejandro\\Documents\\Proyecto Pignatelli\\docs\\Condominio Solaris-Belongings-01032026 - Sheet1.pdf'
text=extract_text(p)
for kw in ['11','round pink vases','MARGHERITA','Margherita','D11']:
    print('\n---',kw,'---')
    i=text.lower().find(kw.lower())
    print('found',i)
    if i!=-1:
        print(text[max(0,i-220):i+260])
print('\nlen',len(text))
