"""Model-specific C7000 PostScript, using commands from Xerox's official PPD.

RAW transport bypasses the driver's rendering/filter path, not printer hardware.
No claims of hardware acknowledgement are made by a successful spool submission.
"""
import base64, math, zlib, shutil
from pathlib import Path
import fitz

PPD_URL='https://www.support.xerox.com/en-us/product/versalink-c7000/content/148618'
ENHANCED='''<</PostRenderingEnhance true
/PostRenderingEnhanceDetails currentpagedevice
1 index get 1 dict copy
dup /Type 33 put
dup /OutputMode (enhanced) put
>> setpagedevice'''

def check_settings(config):
    w,h=float(config['width']),float(config['height'])
    # Conservative supported range. Long banners and custom duplex need separate acceptance.
    if not (105<=w<=297.01 and 148<=h<=432.01 or 148<=w<=432.01 and 105<=h<=297.01):
        raise ValueError('Автопечать C7000: допустимы размеры 105–297 × 148–432 мм, включая поворот. Для других размеров требуется отдельная проверка.')
    if config['media'] not in ('plain','glossy170'): raise ValueError('Носитель не сопоставлен.')
    if config['duplex'] not in (0,1,2): raise ValueError('Недопустимый режим сторон.')
    if config['media']=='glossy170' and config['duplex']: raise ValueError('Глянец 170 г/м²: только одна сторона.')
    if config['duplex'] and sorted((round(w,1),round(h,1))) not in ([210.0,297.0],[297.0,420.0],[148.0,210.0]):
        raise ValueError('Автоматический дуплекс этой версии проверяется только для A3/A4/A5.')
    if not 1<=int(config['copies'])<=999: raise ValueError('Недопустимое число копий.')
    if float(config['margin'])<0 or min(w,h)<=2*float(config['margin']): raise ValueError('Поля превышают размер листа.')

def inspect_queue(name):
    import win32print
    handle=win32print.OpenPrinter(name)
    try:
        info=win32print.GetPrinter(handle,2)
        driver=info['pDriverName']
        if 'C7000' not in driver or 'PS' not in driver:
            raise ValueError('Этот путь предназначен только для подтверждённого Xerox C7000 с PS-драйвером.')
        data=win32print.EnumPrintProcessorDatatypes(None,info['pPrintProcessor'],1)
        if not any(x['pName'].upper()=='RAW' for x in data): raise ValueError('Очередь не предоставляет RAW PostScript. Задание не отправлено.')
        return dict(queue=name,driver=driver,transport='RAW PostScript',deviceAcknowledged=False)
    finally: win32print.ClosePrinter(handle)

def make_ps(doc,destination,config):
    check_settings(config)
    w,h=config['width']*72/25.4,config['height']*72/25.4
    xp,yp=math.ceil(w*1200/72),math.ceil(h*2400/72)
    pixels=xp*yp*len(doc)
    if pixels>2_000_000_000: raise ValueError('Слишком много страниц для задания 1200 × 2400. Разделите документ.')
    if shutil.disk_usage(Path(destination).parent).free<pixels*4: raise ValueError('Недостаточно свободного места для подготовки задания.')
    media='cardstock-glossy' if config['media']=='glossy170' else 'stationery'
    with open(destination,'wb') as output:
        def write(text):output.write(text.encode('ascii'))
        write('\x1b%-12345X@PJL JOB\n@PJL ENTER LANGUAGE = POSTSCRIPT\n%!PS-Adobe-3.0\n')
        write(f'%%Creator: Print Studio 0.2\n%%Pages: {len(doc)}\n%%BoundingBox: 0 0 {math.ceil(w)} {math.ceil(h)}\n%%EndComments\n')
        write('%%BeginSetup\n')
        write(f'<< /PageSize [{w:.8f} {h:.8f}] /ImagingBBox null >> setpagedevice\n')
        write(f'1 dict dup /MediaType ({media}) put setpagedevice\n')
        write(f'<< /Duplex {str(bool(config["duplex"])).lower()} /Tumble {str(config["duplex"]==2).lower()} >> setpagedevice\n')
        write(ENHANCED+'\n')
        write(f'<< /NumCopies {int(config["copies"])} /Collate true >> setpagedevice\n')
        # Abort before showpage if the PS interpreter substitutes the required media or quality.
        write(f'currentpagedevice /MediaType get ({media}) ne {{ /configurationerror signalerror }} if\n')
        write('currentpagedevice /PostRenderingEnhanceDetails get /OutputMode get (enhanced) ne { /configurationerror signalerror } if\n')
        write('%%EndSetup\n')
        for n in range(len(doc)):
            composed=fitz.open()
            converted=None
            try:
                source=doc
                if not doc.is_pdf: converted=fitz.open('pdf',doc.convert_to_pdf()); source=converted
                page=composed.new_page(width=w,height=h)
                m=config['margin']*72/25.4; rect=fitz.Rect(m,m,w-m,h-m)
                clip=fitz.Rect(source[n].rect)
                if config['fill']:
                    ratio=rect.width/rect.height
                    if clip.width/clip.height>ratio:
                        size=clip.height*ratio; clip.x0+=(clip.width-size)/2; clip.x1=clip.x0+size
                    else:
                        size=clip.width/ratio; clip.y0+=(clip.height-size)/2; clip.y1=clip.y0+size
                page.show_pdf_page(rect,source,n,clip=clip,keep_proportion=True)
                write(f'%%Page: {n+1} {n+1}\n/DeviceRGB setcolorspace\n')
                for y in range(0,yp,1024):
                    for x in range(0,xp,2048):
                        area=fitz.Rect(x*72/1200,y*72/2400,min((x+2048)*72/1200,w),min((y+1024)*72/2400,h))
                        pix=page.get_pixmap(matrix=fitz.Matrix(1200/72,2400/72),clip=area,colorspace=fitz.csRGB,alpha=False)
                        left,bottom=pix.x*72/1200,h-(pix.y+pix.height)*72/2400
                        tw,th=pix.width*72/1200,pix.height*72/2400
                        write(f'gsave {left:.8f} {bottom:.8f} translate {tw:.8f} {th:.8f} scale\n')
                        write(f'<< /ImageType 1 /Width {pix.width} /Height {pix.height} /BitsPerComponent 8 /Decode [0 1 0 1 0 1] /Interpolate false /ImageMatrix [{pix.width} 0 0 {-pix.height} 0 {pix.height}] /DataSource currentfile /ASCII85Decode filter /FlateDecode filter >> image\n')
                        data=base64.a85encode(zlib.compress(pix.samples,1))
                        for offset in range(0,len(data),120): output.write(data[offset:offset+120]+b'\n')
                        write('~>\ngrestore\n')
                write('showpage\n')
            finally:
                composed.close()
                if converted:converted.close()
        write('%%Trailer\n%%EOF\n\x1b%-12345X@PJL EOJ\n\x1b%-12345X\n')
    return dict(x=1200,y=2400,widthPixels=xp,heightPixels=yp,pages=len(doc),lossless=True,quality='Enhanced',media=media)

def spool_ps(queue,path):
    import win32print
    inspect_queue(queue)
    handle=win32print.OpenPrinter(queue); job_id=None; started=False
    try:
        job_id=win32print.StartDocPrinter(handle,1,('Print Studio • Enhanced',None,'RAW')); started=True
        with open(path,'rb') as source:
            while True:
                block=source.read(1024*1024)
                if not block:break
                offset=0
                while offset<len(block):
                    count=win32print.WritePrinter(handle,block[offset:])
                    if count<=0:raise RuntimeError('Windows не приняла данные задания.')
                    offset+=count
        win32print.EndDocPrinter(handle); started=False
        return job_id
    except Exception:
        if started: win32print.AbortPrinter(handle)
        raise
    finally:win32print.ClosePrinter(handle)
