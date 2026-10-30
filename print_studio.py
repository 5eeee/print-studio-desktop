import sys, os
import fitz
from PySide6.QtCore import Qt, QSizeF, QRectF, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPageSize, QPageLayout
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QComboBox,QDoubleSpinBox,QSpinBox,QFileDialog,QMessageBox,QScrollArea
from PySide6.QtPrintSupport import QPrinter,QPrinterInfo,QPrintDialog
import json, subprocess, tempfile, shutil, concurrent.futures
from pathlib import Path
from ps_job import check_settings, inspect_queue, make_ps, spool_ps

class Studio(QMainWindow):
    def __init__(self):
        super().__init__(); self.doc=None; self.image=None; self.setWindowTitle('Print Studio 0.2 • проверяемая печать'); self.resize(1180,820)
        self.printer=QPrinter(QPrinter.HighResolution); self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1); self.pending=None; self.timer=QTimer(self); self.timer.timeout.connect(self.poll_job); self.timer.start(250)
        root=QWidget(); self.setCentralWidget(root); layout=QHBoxLayout(root)
        side=QWidget(); side.setFixedWidth(320); controls=QVBoxLayout(side); controls.setSpacing(5); panel=QScrollArea(); panel.setWidgetResizable(True); panel.setFixedWidth(345); panel.setWidget(side); layout.addWidget(panel)
        title=QLabel('PRINT STUDIO'); title.setObjectName('title'); controls.addWidget(title)
        controls.addWidget(QLabel('Документ → лист → печать'))
        self.addbutton(controls,'Открыть PDF или изображение',self.open)
        self.filename=QLabel('Файл не выбран'); self.filename.setWordWrap(True); controls.addWidget(self.filename)
        self.page=QSpinBox(); self.page.setMinimum(1); self.field(controls,'Страница предпросмотра',self.page)
        self.queue=QComboBox(); self.queue.addItems(QPrinterInfo.availablePrinterNames()); self.field(controls,'Принтер',self.queue)
        for i in range(self.queue.count()):
            if 'C7000' in self.queue.itemText(i) and 'V4' in self.queue.itemText(i): self.queue.setCurrentIndex(i); break
        self.format=QComboBox(); self.format.addItems(['A3','A4','A5','Свой размер']); self.field(controls,'Размер листа',self.format)
        self.width=QDoubleSpinBox(); self.height=QDoubleSpinBox()
        for box,value,label in [(self.width,297,'Ширина, мм'),(self.height,420,'Высота, мм')]:
            box.setRange(20,2000); box.setValue(value); self.field(controls,label,box); box.valueChanged.connect(self.preview)
        self.mode=QComboBox(); self.mode.addItems(['Вписать целиком','Заполнить с обрезкой']); self.field(controls,'Размещение',self.mode)
        self.margin=QDoubleSpinBox(); self.margin.setRange(0,50); self.margin.setValue(5); self.field(controls,'Поля макета, мм',self.margin)
        self.duplex=QComboBox(); self.duplex.addItems(['Одна сторона','Две стороны • длинный край','Две стороны • короткий край']); self.field(controls,'Стороны',self.duplex)
        self.media=QComboBox(); self.media.addItems(['Глянец 170 г/м²','Обычная бумага','Другой носитель']); self.field(controls,'Автоматический тип носителя',self.media)
        self.copies=QSpinBox(); self.copies.setRange(1,999); self.field(controls,'Копии',self.copies)
        self.addbutton(controls,'Повернуть лист',self.rotate)
        self.addbutton(controls,'Проверить готовность очереди',self.validate_native)
        self.addbutton(controls,'Печатать автоматически',self.print_native)
        self.addbutton(controls,'Диагностика драйвера → буфер',self.scan_native)
        hint=QLabel('Прямая печать PostScript: команды носителя и Enhanced из PPD Xerox. Растр 1200 × 2400. Приём задания Windows не подтверждает физический результат. Печатаются все страницы; для пробы откройте одностраничный PDF.'); hint.setWordWrap(True); controls.addWidget(hint); controls.addStretch()
        area=QScrollArea(); area.setWidgetResizable(True); self.canvas=QLabel('Откройте документ\nPDF • JPEG • PNG • TIFF • BMP • WebP'); self.canvas.setAlignment(Qt.AlignCenter); area.setWidget(self.canvas); layout.addWidget(area)
        self.statusBar().showMessage('Готово • физический отпечаток требует проверки на принтере')
        self.page.valueChanged.connect(self.preview); self.mode.currentIndexChanged.connect(self.preview); self.margin.valueChanged.connect(self.preview); self.format.currentIndexChanged.connect(self.change_format)
        self.setStyleSheet('QWidget{font-family:Segoe UI;font-size:12px;color:#29252a;background:#fff;} QMainWindow,QScrollArea{background:#f3f0f1;} QPushButton{background:#c92239;color:white;border:0;border-radius:7px;padding:9px;} QPushButton:hover{background:#a4152b;} QComboBox,QSpinBox,QDoubleSpinBox{border:1px solid #d9ced1;border-radius:5px;padding:4px;} QLabel#title{font-size:26px;font-weight:800;color:#c92239;}')
    def field(self,l,t,w): l.addWidget(QLabel(t)); l.addWidget(w)
    def addbutton(self,l,t,f):
        b=QPushButton(t); b.clicked.connect(f); l.addWidget(b)
    def open(self):
        path,_=QFileDialog.getOpenFileName(self,'Открыть','','Документы (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)')
        if not path:return
        try:
            doc=fitz.open(path)
            if doc.needs_pass: raise ValueError('PDF защищён паролем. Откройте незашифрованную копию.')
            if self.doc:self.doc.close()
            self.doc=doc; self.filename.setText(os.path.basename(path)); self.page.setMaximum(len(doc)); self.page.setValue(1); self.preview()
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
            w,h=self.width.value(),self.height.value(); scale=min(720/w,680/h); out=QImage(round(w*scale),round(h*scale),QImage.Format_RGB888); out.fill(Qt.white)
            p=QPainter(out); p.setRenderHint(QPainter.SmoothPixmapTransform); m=self.margin.value()*scale
            self.draw(p,QRectF(m,m,out.width()-2*m,out.height()-2*m),self.render(self.page.value()-1,100)); p.end(); self.canvas.setPixmap(QPixmap.fromImage(out))
            self.statusBar().showMessage(f'{w:g} × {h:g} мм • страница {self.page.value()} / {len(self.doc)} • предпросмотр размещения')
        except Exception as e: self.statusBar().showMessage(str(e))
    def config_native(self):
        if self.media.currentIndex()==2: raise ValueError('Выберите глянец 170 или обычную бумагу. Произвольный носитель ещё не сопоставлен.')
        if self.media.currentIndex()==0 and self.duplex.currentIndex(): raise ValueError('Глянец 170 г/м² требует односторонней печати.')
        return dict(queue=self.queue.currentText(),width=self.width.value(),height=self.height.value(),margin=self.margin.value(),fill=bool(self.mode.currentIndex()),media='glossy170' if self.media.currentIndex()==0 else 'plain',duplex=self.duplex.currentIndex(),copies=self.copies.value())
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
            if action=='print' and not self.doc: raise ValueError('Сначала откройте документ.')
            # Independent PDF snapshot keeps document access on the worker thread safe.
            snapshot=self.doc.convert_to_pdf() if self.doc and not self.doc.is_pdf else (self.doc.tobytes() if self.doc else None)
            self.pending_action=action
            self.pending=self.pool.submit(self.worker_native,config,action,snapshot)
            self.statusBar().showMessage('Проверка возможностей драйвера…')
        except Exception as e: QMessageBox.warning(self,'Проверка',str(e))
    def worker_native(self,config,action,snapshot):
        folder=tempfile.mkdtemp(prefix='PrintStudio-job-')
        try:
            if action=='scan':return self.helper(config,folder,'scan')
            check_settings(config)
            report=inspect_queue(config['queue'])
            report.update(ok=True,message='Очередь поддерживает отправку RAW PostScript. Будут запрошены Enhanced и выбранный тип бумаги. Физическое разрешение и результат аппарата ещё не подтверждены.')
            if action!='print':return report
            document=fitz.open('pdf',snapshot)
            try:
                path=str(Path(folder)/'job.ps')
                grid=make_ps(document,path,config)
            finally:document.close()
            job_id=spool_ps(config['queue'],path)
            report.update(sourceGrid=grid,jobId=job_id,message=f'Задание №{job_id} передано Windows: растр 1200 × 2400, команды Enhanced и типа бумаги включены. Проверьте экран аппарата и контрольный отпечаток.')
            return report
        finally:
            shutil.rmtree(folder,ignore_errors=True)
    def poll_job(self):
        if not self.pending or not self.pending.done(): return
        future=self.pending; self.pending=None
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
    def closeEvent(self,event):
        if self.pending:
            QMessageBox.information(self,'Задание выполняется','Дождитесь завершения проверки или передачи задания.'); event.ignore(); return
        self.pool.shutdown(wait=False); event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv); window=Studio(); window.show(); sys.exit(app.exec())
