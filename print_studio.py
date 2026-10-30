import sys, os
import fitz
from PySide6.QtCore import Qt, QSizeF, QRectF, QTimer, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QPixmap, QPainter, QPageSize, QPageLayout, QImageReader
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QComboBox,QDoubleSpinBox,QSpinBox,QFileDialog,QMessageBox,QScrollArea,QFrame,QGridLayout,QSizePolicy,QLineEdit,QCheckBox
from PySide6.QtPrintSupport import QPrinter,QPrinterInfo,QPrintDialog
import json, subprocess, tempfile, shutil, concurrent.futures
from pathlib import Path
from ps_job import check_settings, inspect_queue, make_ps, spool_ps

class Studio(QMainWindow):
    def __init__(self):
        super().__init__(); self.doc=None; self.image=None
        self.setWindowTitle('Print Studio 0.4.1'); self.resize(1200,820); self.setMinimumSize(960,640)
        self.printer=QPrinter(QPrinter.HighResolution); self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1); self.pending=None
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll_job); self.timer.start(250)
        root=QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        outer=QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        header=QFrame(); header.setObjectName('header'); head=QHBoxLayout(header); head.setContentsMargins(24,16,24,16)
        logo=QLabel('P / S'); logo.setObjectName('logo'); head.addWidget(logo)
        brand=QVBoxLayout(); brand.setSpacing(0); name=QLabel('Print Studio'); name.setObjectName('brand'); brand.addWidget(name)
        sub=QLabel('Печать, которую удобно готовить'); sub.setObjectName('muted'); brand.addWidget(sub); head.addLayout(brand); head.addStretch()
        badge=QLabel('XEROX C7000  /  PS'); badge.setObjectName('badge'); head.addWidget(badge)
        self.addbutton(head,'＋  Открыть файл',self.open,'primary'); outer.addWidget(header)
        body=QHBoxLayout(); body.setContentsMargins(20,20,20,16); body.setSpacing(20); outer.addLayout(body,1)
        stage=QFrame(); stage.setObjectName('stage'); stagebox=QVBoxLayout(stage); stagebox.setContentsMargins(20,16,20,16)
        bar=QHBoxLayout(); label=QLabel('ПРЕДПРОСМОТР'); label.setObjectName('eyebrow'); bar.addWidget(label); bar.addStretch()
        self.page=QSpinBox(); self.page.setMinimum(1); self.page.setFixedWidth(74); self.page.setToolTip('Страница предпросмотра. Диапазон печати задаётся в правой панели.')
        bar.addWidget(QLabel('Страница')); bar.addWidget(self.page); self.addbutton(bar,'↻  Повернуть лист',self.rotate,'secondary'); stagebox.addLayout(bar)
        area=QScrollArea(); area.setObjectName('previewArea'); area.setWidgetResizable(True); area.setFrameShape(QFrame.NoFrame)
        self.canvas=QLabel('Ваш следующий отпечаток\n\nОткройте PDF или изображение\nPDF · JPEG · PNG · TIFF · BMP · WebP'); self.canvas.setObjectName('canvas'); self.canvas.setAlignment(Qt.AlignCenter)
        self.previewArea=area; self.canvas.setMinimumSize(1,1); self.canvas.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Ignored); area.setWidget(self.canvas); stagebox.addWidget(area,1)
        self.filename=QLabel('Документ не выбран'); self.filename.setObjectName('filename'); self.filename.setWordWrap(True); stagebox.addWidget(self.filename)
        body.addWidget(stage,1)
        panel=QScrollArea(); panel.setFixedWidth(330); panel.setWidgetResizable(True); panel.setFrameShape(QFrame.NoFrame); panel.setObjectName('settingsScroll')
        side=QWidget(); side.setObjectName('settings'); controls=QVBoxLayout(side); controls.setContentsMargins(18,18,18,18); controls.setSpacing(10); panel.setWidget(side); body.addWidget(panel)
        self.section(controls,'01','Принтер и бумага')
        self.queue=QComboBox(); self.queue.addItems(QPrinterInfo.availablePrinterNames()); self.field(controls,'Очередь печати',self.queue)
        for i in range(self.queue.count()):
            if 'C7000' in self.queue.itemText(i) and 'V4' in self.queue.itemText(i): self.queue.setCurrentIndex(i); break
        self.media=QComboBox(); self.media.addItems(['Глянец · 170 г/м²','Обычная бумага','Другой носитель']); self.field(controls,'Носитель',self.media)
        self.section(controls,'02','Размер и размещение')
        self.format=QComboBox(); self.format.addItems(['A3','A4','A5','Свой размер']); self.field(controls,'Формат листа',self.format)
        self.width=QDoubleSpinBox(); self.height=QDoubleSpinBox(); dims=QHBoxLayout(); dims.setSpacing(10)
        for box,value,label in [(self.width,297,'Ширина, мм'),(self.height,420,'Высота, мм')]:
            box.setRange(20,2000); box.setValue(value); box.setDecimals(1); col=QVBoxLayout(); self.field(col,label,box); dims.addLayout(col)
        controls.addLayout(dims)
        self.mode=QComboBox(); self.mode.addItems(['Вписать целиком','Заполнить с обрезкой']); self.field(controls,'Размещение изображения',self.mode)
        self.margin=QDoubleSpinBox(); self.margin.setRange(0,50); self.margin.setValue(5); self.margin.setSuffix(' мм'); self.field(controls,'Поля макета',self.margin)
        self.section(controls,'03','Параметры задания')
        self.duplex=QComboBox(); self.duplex.addItems(['Одна сторона','Две стороны · длинный край','Две стороны · короткий край']); self.field(controls,'Стороны',self.duplex)
        self.copies=QSpinBox(); self.copies.setRange(1,999); self.field(controls,'Количество копий',self.copies)
        self.range=QLineEdit(); self.range.setPlaceholderText('Все или 1-3, 5, 8'); self.field(controls,'Страницы для печати',self.range)
        self.advanced=QCheckBox('Расширенные параметры'); controls.addWidget(self.advanced)
        self.qualityMode=QComboBox(); self.qualityMode.addItems(['Стандартное','Повышенное','Фото']); self.qualityMode.setCurrentIndex(1); self.field(controls,'Режим качества Xerox',self.qualityMode)
        quality=QLabel('Подготовка 1200 × 2400'); quality.setObjectName('quality'); controls.addWidget(quality)
        hint=QLabel('Нулевые поля не отменяют границы печати аппарата. Для первой пробы откройте одностраничный файл.'); hint.setWordWrap(True); hint.setObjectName('hint'); controls.addWidget(hint)
        diagnostics=self.addbutton(controls,'Диагностика драйвера',self.scan_native,'text'); diagnostics.hide(); hint.hide(); self.advanced.toggled.connect(diagnostics.setVisible); self.advanced.toggled.connect(hint.setVisible); controls.addStretch()
        footer=QFrame(); footer.setObjectName('footer'); foot=QHBoxLayout(footer); foot.setContentsMargins(24,14,24,14)
        note=QLabel('Готовим точный макет.\nРезультат на аппарате проверяется контрольным отпечатком.'); note.setObjectName('muted'); foot.addWidget(note,1)
        self.addbutton(foot,'Проверить очередь',self.validate_native,'secondary'); self.printButton=self.addbutton(foot,'Печатать автоматически  →',self.print_native,'primary'); outer.addWidget(footer)
        self.setAcceptDrops(True)
        self.settingsFile=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'PrintStudio'/'preferences.json'
        self.restore_settings()
        self.statusBar().showMessage('Готово к работе')
        self.page.valueChanged.connect(self.preview); self.mode.currentIndexChanged.connect(self.preview); self.margin.valueChanged.connect(self.preview); self.format.currentIndexChanged.connect(self.change_format)
        self.width.valueChanged.connect(self.preview); self.height.valueChanged.connect(self.preview)
        self.setStyleSheet("""
            QWidget {font-family:'Segoe UI'; font-size:12px; color:#242831;}
            QMainWindow, QWidget#root {background:#f4f5f7;}
            QFrame#header,QFrame#footer {background:#fff; border:0;}
            QFrame#header {border-bottom:1px solid #e4e6eb;}
            QFrame#footer {border-top:1px solid #e4e6eb;}
            QLabel#logo {background:#d61f3d;color:white;font-size:19px;font-weight:800;border-radius:12px;padding:13px;}
            QLabel#brand {font-size:24px;font-weight:750;letter-spacing:-1px;}
            QLabel#muted {color:#737b88;font-size:11px;}
            QLabel#badge {color:#9d2840;background:#fff0f3;border:1px solid #f6d5dd;border-radius:6px;padding:8px;font-size:10px;font-weight:700;}
            QFrame#stage {background:#e9ecf0;border:1px solid #e0e4e9;border-radius:14px;}
            QScrollArea#previewArea,QLabel#canvas {background:transparent;border:0;color:#7c8491;}
            QLabel#canvas {font-size:16px;}
            QLabel#eyebrow {font-size:10px;font-weight:700;color:#6a7280;letter-spacing:2px;}
            QLabel#filename {color:#677180;font-size:11px;padding-top:8px;}
            QScrollArea#settingsScroll,QWidget#settings {background:white;border-radius:14px;}
            QLabel#section {font-size:15px;font-weight:700;padding-top:10px;padding-bottom:3px;}
            QLabel#field {color:#747c89;font-size:11px;}
            QComboBox,QSpinBox,QDoubleSpinBox {background:#f8f9fb;border:1px solid #e1e5eb;border-radius:7px;padding:7px;color:#262c35;selection-background-color:#d61f3d;}
            QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:1px solid #d61f3d;}
            QComboBox::drop-down {border:0;width:22px;}
            QComboBox QAbstractItemView {background:white;color:#242831;selection-background-color:#ffedf1;selection-color:#a21430;}
            QPushButton {border-radius:8px;padding:10px 14px;font-weight:600;}
            QPushButton#primary {background:#d61f3d;color:white;border:1px solid #d61f3d;}
            QPushButton#primary:hover {background:#b91531;}
            QPushButton#secondary {background:white;color:#454e5c;border:1px solid #d9dfe7;}
            QPushButton#secondary:hover {background:#f5f6f8;}
            QPushButton#text {background:transparent;color:#8a3448;border:0;text-align:left;padding-left:0;}
            QLabel#quality {background:#fff1f4;border:1px solid #f8dfe5;border-radius:8px;color:#a91b37;padding:12px;font-weight:650;}
            QLabel#hint {color:#848b97;font-size:10px;line-height:1.5;}
            QStatusBar {background:#f4f5f7;color:#89919d;font-size:10px;border:0;}
            QScrollBar:vertical {background:transparent;width:7px;margin:4px 0;}
            QScrollBar::handle:vertical {background:#cbd1da;border-radius:3px;min-height:30px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
        """)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"previewArea"): QTimer.singleShot(0,self.preview)
    def field(self,l,t,w):
        label=QLabel(t); label.setObjectName('field'); l.addWidget(label); l.addWidget(w)
    def section(self,l,n,t):
        label=QLabel(n+'  /  '+t); label.setObjectName('section'); l.addWidget(label)
    def addbutton(self,l,t,f,kind='secondary'):
        b=QPushButton(t); b.setObjectName(kind); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(f); l.addWidget(b); return b
    def open(self):
        path,_=QFileDialog.getOpenFileName(self,'Открыть','','Документы (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)')
        if path:self.load_path(path)
    def load_path(self,path):
        try:
            try:doc=fitz.open(path)
            except Exception:
                reader=QImageReader(path); reader.setAutoTransform(True); image=reader.read()
                if image.isNull():raise ValueError('Не удалось прочитать файл. Он повреждён или формат не поддерживается.')
                data=QByteArray(); buffer=QBuffer(data); buffer.open(QIODevice.WriteOnly)
                try:
                    if not image.save(buffer,'PNG'):raise ValueError('Не удалось преобразовать изображение.')
                finally:buffer.close()
                doc=fitz.open('png',bytes(data))
            if doc.needs_pass:
                doc.close(); raise ValueError('PDF защищён паролем. Откройте незашифрованную копию.')
            if not len(doc):
                doc.close(); raise ValueError('В документе нет страниц.')
            if self.doc:self.doc.close()
            self.doc=doc; self.range.clear(); self.filename.setText(os.path.basename(path)); self.page.setMaximum(len(doc)); self.page.setValue(1); self.preview()
        except Exception as e: QMessageBox.warning(self,'Не удалось открыть',str(e))
    def change_format(self):
        sizes=[(297,420),(210,297),(148,210)]
        if self.format.currentIndex()<3:
            w,h=sizes[self.format.currentIndex()]; self.width.setValue(w); self.height.setValue(h)
    def rotate(self):
        w,h=self.width.value(),self.height.value(); self.width.setValue(h); self.height.setValue(w)
    def render(self,index,dpi):
        page=self.doc[index]; dpi=min(dpi,72*(40000000/max(1,page.rect.width*page.rect.height))**0.5); pix=page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False)
        return QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
    def draw(self,painter,rect,image):
        scale=max(rect.width()/image.width(),rect.height()/image.height()) if self.mode.currentIndex() else min(rect.width()/image.width(),rect.height()/image.height())
        w,h=image.width()*scale,image.height()*scale
        painter.save(); painter.setClipRect(rect); painter.drawImage(QRectF(rect.center().x()-w/2,rect.center().y()-h/2,w,h),image); painter.restore()
    def preview(self,*args):
        if not self.doc:return
        try:
            w,h=self.width.value(),self.height.value(); scale=min(max(120,self.previewArea.viewport().width()-40)/w,max(120,self.previewArea.viewport().height()-30)/h); out=QImage(round(w*scale),round(h*scale),QImage.Format_RGB888); out.fill(Qt.white)
            p=QPainter(out); p.setRenderHint(QPainter.SmoothPixmapTransform); m=self.margin.value()*scale
            try:
                if min(w,h)<=2*self.margin.value():raise ValueError('Уменьшите поля: они превышают размер листа.')
                self.draw(p,QRectF(m,m,out.width()-2*m,out.height()-2*m),self.render(self.page.value()-1,100))
            finally:p.end()
            self.canvas.setPixmap(QPixmap.fromImage(out))
            self.statusBar().showMessage(f'{w:g} × {h:g} мм • страница {self.page.value()} / {len(self.doc)} • предпросмотр размещения')
        except Exception as e: self.statusBar().showMessage(str(e))
    def config_native(self):
        if self.media.currentIndex()==2: raise ValueError('Выберите глянец 170 или обычную бумагу. Произвольный носитель ещё не сопоставлен.')
        if self.media.currentIndex()==0 and self.duplex.currentIndex(): raise ValueError('Глянец 170 г/м² требует односторонней печати.')
        return dict(queue=self.queue.currentText(),width=self.width.value(),height=self.height.value(),margin=self.margin.value(),fill=bool(self.mode.currentIndex()),media='glossy170' if self.media.currentIndex()==0 else 'plain',duplex=self.duplex.currentIndex(),copies=self.copies.value(),quality=['standard','enhanced','photographic'][self.qualityMode.currentIndex()])
    def helper(self,config,folder,action):
        config=dict(config,action=action)
        request=Path(folder)/'request.json'; request.write_text(json.dumps(config),encoding='utf-8')
        script=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'native_print.ps1'
        run=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(script),'-Request',str(request)],capture_output=True,creationflags=0x08000000,timeout=600)
        result=Path(folder)/'result.json'
        if not result.exists(): raise RuntimeError('Сбой PrintTicket: '+run.stderr.decode('utf-8',errors='replace')[-1500:])
        report=json.loads(result.read_text(encoding='utf-8-sig'))
        log=Path(os.environ.get('LOCALAPPDATA',folder))/'PrintStudio'/'last-check.json'; log.parent.mkdir(parents=True,exist_ok=True); log.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return report
    def begin_native(self,action):
        if self.pending: return
        try:
            config=self.config_native()
            try:self.save_settings()
            except OSError:pass
            if action=='print' and not self.doc: raise ValueError('Сначала откройте документ.')
            # Independent PDF snapshot keeps document access on the worker thread safe.
            if action!='scan':check_settings(config)
            selected=self.selected_pages() if self.doc and action=='print' else []
            snapshot=(self.doc.convert_to_pdf() if not self.doc.is_pdf else self.doc.tobytes()) if self.doc and action=='print' else None
            if snapshot and action=='print':
                original=fitz.open('pdf',snapshot); subset=fitz.open()
                try:
                    for index in selected:subset.insert_pdf(original,from_page=index,to_page=index)
                    snapshot=subset.tobytes()
                finally:original.close(); subset.close()
            self.pending_action=action
            self.pending=self.pool.submit(self.worker_native,config,action,snapshot)
            self.printButton.setEnabled(False)
            self.statusBar().showMessage('Подготовка задания…')
        except Exception as e: QMessageBox.warning(self,'Проверка',str(e))
    def worker_native(self,config,action,snapshot):
        folder=tempfile.mkdtemp(prefix='PrintStudio-job-')
        try:
            if action=='scan':return self.helper(config,folder,'scan')
            check_settings(config)
            report=inspect_queue(config['queue'])
            report.update(ok=True,message='Очередь поддерживает отправку RAW PostScript. Будут запрошены выбранный режим качества и тип бумаги. Физическое разрешение и результат аппарата ещё не подтверждены.')
            if action!='print':return report
            document=fitz.open('pdf',snapshot)
            try:
                path=str(Path(folder)/'job.ps')
                grid=make_ps(document,path,config)
            finally:document.close()
            job_id=spool_ps(config['queue'],path)
            report.update(sourceGrid=grid,jobId=job_id,message=f'Задание №{job_id} передано Windows: растр 1200 × 2400, команды выбранного качества и типа бумаги включены. Проверьте экран аппарата и контрольный отпечаток.')
            return report
        finally:
            shutil.rmtree(folder,ignore_errors=True)
    def poll_job(self):
        if not self.pending or not self.pending.done(): return
        future=self.pending; self.pending=None; self.printButton.setEnabled(True)
        try:
            report=future.result()
            if self.pending_action=='scan':
                QApplication.clipboard().setText(json.dumps(report,ensure_ascii=False,indent=2))
                QMessageBox.information(self,'Диагностика','Сведения о возможностях драйвера скопированы. Документы, пароли и закрытые блоки настроек не включены.')
            elif report.get('ok'):
                QMessageBox.information(self,'Результат',report['message'])
            else:
                QMessageBox.warning(self,'Печать остановлена',report.get('message','Не удалось проверить параметры')+'\n\nНажмите «Диагностика драйвера → буфер» и передайте результат для настройки точного профиля Xerox. Никакие параметры очереди не изменены.')
            self.statusBar().showMessage(report.get('message','Проверка завершена'))
        except Exception as e: QMessageBox.critical(self,'Ошибка',str(e))
    def validate_native(self): self.begin_native('validate')
    def scan_native(self): self.begin_native('scan')
    def print_native(self): self.begin_native('print')
    def selected_pages(self):
        text=self.range.text().strip().replace('–','-').replace('—','-')
        if not text:return list(range(len(self.doc)))
        result=[]
        for token in text.split(','):
            bounds=token.strip().split('-')
            if len(bounds)>2:raise ValueError('Страницы: используйте 1-3, 5, 8.')
            start=int(bounds[0]); end=int(bounds[-1])
            if not 1<=start<=end<=len(self.doc):raise ValueError('Диапазон выходит за пределы документа.')
            for n in range(start-1,end):
                if n not in result:result.append(n)
        return result
    def save_settings(self):
        data={name:getattr(self,name).value() for name in ('width','height','margin','copies')}
        data.update({name:getattr(self,name).currentIndex() for name in ('format','mode','media','duplex','qualityMode')})
        data['queue']=self.queue.currentText()
        self.settingsFile.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.settingsFile.with_suffix('.tmp'); temporary.write_text(json.dumps(data),encoding='utf-8'); os.replace(temporary,self.settingsFile)
    def restore_settings(self):
        try:
            data=json.loads(self.settingsFile.read_text(encoding='utf-8'))
            if not isinstance(data,dict):return
            for name in ('format','mode','media','duplex','qualityMode'):
                box=getattr(self,name); value=int(data.get(name,box.currentIndex()))
                if 0<=value<box.count():box.setCurrentIndex(value)
            for name in ('width','height','margin','copies'):
                if name in data:getattr(self,name).setValue(data[name])
            index=self.queue.findText(data.get('queue',''))
            if index>=0:self.queue.setCurrentIndex(index)
        except (OSError,ValueError,TypeError,OverflowError):pass
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if urls and urls[0].isLocalFile():self.load_path(urls[0].toLocalFile())
    def closeEvent(self,event):
        if self.pending:
            QMessageBox.information(self,'Задание выполняется','Дождитесь завершения проверки или передачи задания.'); event.ignore(); return
        try:self.save_settings()
        except OSError:pass
        self.pool.shutdown(wait=False); event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv); window=Studio(); window.show(); sys.exit(app.exec())
