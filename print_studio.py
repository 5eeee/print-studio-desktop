import sys, os
import fitz
from PySide6.QtCore import Qt, QSizeF, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QPageSize, QPageLayout
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QComboBox,QDoubleSpinBox,QSpinBox,QFileDialog,QMessageBox,QScrollArea
from PySide6.QtPrintSupport import QPrinter,QPrinterInfo,QPrintDialog

class Studio(QMainWindow):
    def __init__(self):
        super().__init__(); self.doc=None; self.image=None; self.setWindowTitle('Print Studio • A3'); self.resize(1180,820)
        self.printer=QPrinter(QPrinter.HighResolution)
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
        self.media=QComboBox(); self.media.addItems(['Глянец 170 г/м²','Обычная бумага','Другой носитель']); self.field(controls,'Профиль носителя (напоминание)',self.media)
        self.copies=QSpinBox(); self.copies.setRange(1,999); self.field(controls,'Копии',self.copies)
        self.addbutton(controls,'Повернуть лист',self.rotate)
        self.addbutton(controls,'Свойства драйвера / печать…',self.print_file)
        hint=QLabel('Качество и точный тип носителя задайте в свойствах Xerox перед печатью. Нулевые поля макета не отменяют непечатаемую область аппарата.'); hint.setWordWrap(True); controls.addWidget(hint); controls.addStretch()
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
    def print_file(self):
        if not self.doc:return
        if self.media.currentIndex()==0 and self.duplex.currentIndex():
            QMessageBox.warning(self,'Несовместимый режим','Для C7000 глянец 170 г/м² печатается односторонне.'); return
        self.printer.setPrinterName(self.queue.currentText())
        self.printer.setPageSize(QPageSize(QSizeF(self.width.value(),self.height.value()),QPageSize.Millimeter,'Custom'))
        self.printer.setFullPage(True); self.printer.setCopyCount(self.copies.value())
        self.printer.setDuplex([QPrinter.DuplexNone,QPrinter.DuplexLongSide,QPrinter.DuplexShortSide][self.duplex.currentIndex()])
        dialog=QPrintDialog(self.printer,self); dialog.setMinMax(1,len(self.doc))
        if dialog.exec()!=QPrintDialog.Accepted:return
        if self.media.currentIndex()==0 and self.printer.duplex()!=QPrinter.DuplexNone:
            QMessageBox.warning(self,'Проверьте стороны','Отключите дуплекс для глянца 170 г/м².'); return
        try:
            painter=QPainter()
            if not painter.begin(self.printer):raise RuntimeError('Драйвер не начал печать')
            try:
                start=max(1,self.printer.fromPage() or 1); end=min(len(self.doc),self.printer.toPage() or len(self.doc))
                for n in range(start-1,end):
                    if n>start-1 and not self.printer.newPage():raise RuntimeError('Ошибка новой страницы')
                    dpi=self.printer.resolution(); rect=self.printer.pageLayout().fullRectPixels(dpi); m=self.margin.value()*dpi/25.4
                    printable=self.printer.pageLayout().paintRectPixels(dpi)
                    target=QRectF(rect).adjusted(m,m,-m,-m).intersected(QRectF(printable))
                    if target.isEmpty():raise RuntimeError('Поля превышают размер страницы')
                    # PDF/vector sources render at up to 600 ppi; device quality remains a driver setting.
                    image=self.render(n,min(dpi,600)); self.draw(painter,target,image)
            finally:painter.end()
            self.statusBar().showMessage('Задание передано Windows. Проверьте очередь и отпечаток.')
        except Exception as e: QMessageBox.critical(self,'Ошибка печати',str(e))

if __name__=='__main__':
    app=QApplication(sys.argv); window=Studio(); window.show(); sys.exit(app.exec())
