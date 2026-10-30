import sys,tempfile,unittest,json,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fitz
from PIL import Image
from PySide6.QtWidgets import QApplication,QMessageBox
import print_studio as ui
import ps_job
app=QApplication.instance() or QApplication([])
class Audit(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.w=ui.Studio();self.w.settingsFile=self.root/'prefs.json'
  self.messages=[];self.old=QMessageBox.warning;QMessageBox.warning=lambda *a:self.messages.append(a[-1])
 def tearDown(self):
  QMessageBox.warning=self.old;self.w.pending=None;self.w.close()
  if self.w.doc:self.w.doc.close()
  self.tmp.cleanup()
 def test_formats(self):
  for ext in ('jpg','png','bmp','webp','tiff'):
   im=Image.new('RGB',(400,300),'red');p=self.root/('image.'+ext);im.save(p);self.w.load_path(str(p));self.assertEqual(len(self.w.doc),1);self.w.preview();self.assertFalse(self.w.canvas.pixmap().isNull())
  p=self.root/'cmyk.jpg';Image.new('CMYK',(60,40),(0,255,0,0)).save(p);self.w.load_path(str(p));self.w.preview();self.assertFalse(self.messages)
 def test_pdf_pages_blank_rotated(self):
  d=fitz.open();d.new_page();p=d.new_page();p.insert_text((30,30),'Page 2');p.set_rotation(90);path=self.root/'test.pdf';d.save(path);d.close();self.w.load_path(str(path));self.w.page.setValue(2);self.w.preview();self.assertEqual(self.w.page.maximum(),2);self.assertFalse(self.messages)
 def test_bad_and_encrypted_keep_document(self):
  p=self.root/'ok.png';Image.new('RGB',(20,20)).save(p);self.w.load_path(str(p));old=self.w.doc
  bad=self.root/'bad.pdf';bad.write_bytes(b'garbage');self.w.load_path(str(bad));self.assertIs(self.w.doc,old)
  d=fitz.open();d.new_page();p=self.root/'locked.pdf';d.save(p,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='test-owner',user_pw='test-user');d.close();self.w.load_path(str(p));self.assertIs(self.w.doc,old);self.assertEqual(len(self.messages),2)
 def test_range(self):
  self.w.doc=fitz.open()
  for i in range(8):self.w.doc.new_page()
  self.w.range.setText('1–3, 5, 8, 1');self.assertEqual(self.w.selected_pages(),[0,1,2,4,7])
  for text in ('0','9','3-1','1,','abc'):
   self.w.range.setText(text)
   with self.assertRaises(ValueError):self.w.selected_pages()
 def test_preferences(self):
  self.w.margin.setValue(9);self.w.qualityMode.setCurrentIndex(2);self.w.save_settings();self.w.margin.setValue(1);self.w.restore_settings();self.assertEqual(self.w.margin.value(),9);self.assertEqual(self.w.qualityMode.currentIndex(),2)
  for value in ('[]','null','{broken','{"copies":null}'):
   self.w.settingsFile.write_text(value);self.w.restore_settings()
 def test_guards(self):
  c=self.w.config_native();c.update(width=105,height=148)
  for invalid in (dict(c,duplex=1),dict(c,margin=100),dict(c,margin=float('nan')),dict(c,quality='fake')):
   with self.assertRaises(ValueError):ps_job.check_settings(invalid)
 def test_worker_pipeline(self):
  d=fitz.open();p=d.new_page(width=100,height=100);p.insert_text((10,20),'TEST');d.new_page();snapshot=d.tobytes();d.close()
  config=self.w.config_native();config.update(width=105,height=148,queue='mock')
  oldinspect,oldspool=ui.inspect_queue,ui.spool_ps
  ui.inspect_queue=lambda q:{'queue':q};captured=[]
  def spool(q,p):
   data=Path(p).read_bytes();self.assertIn(b'%%Pages: 2',data);self.assertIn(b'/MediaType (cardstock-glossy)',data);self.assertIn(b'/OutputMode (enhanced)',data);captured.append(data);return 42
  ui.spool_ps=spool
  try:r=self.w.worker_native(config,'print',snapshot)
  finally:ui.inspect_queue,ui.spool_ps=oldinspect,oldspool
  self.assertTrue(r['ok']);self.assertEqual(r['jobId'],42);self.assertEqual(r['sourceGrid']['x'],1200);self.assertEqual(len(captured),1)
 def test_mock_spool_partial_and_failure(self):
  class Spool:
   def OpenPrinter(self,q):return 1
   def GetPrinter(self,*a):return {'pDriverName':'Xerox VersaLink C7000 V4 PS','pPrintProcessor':'winprint'}
   def EnumPrintProcessorDatatypes(self,*a):return [{'pName':'RAW'}]
   def ClosePrinter(self,h):pass
   def StartDocPrinter(self,*a):return 7
   def WritePrinter(self,h,data):self.data.extend(data[:7]);return min(7,len(data))
   def EndDocPrinter(self,h):pass
   def AbortPrinter(self,h):self.aborted=True
  stub=Spool();stub.data=bytearray();stub.aborted=False;previous=sys.modules.get('win32print');sys.modules['win32print']=stub
  path=self.root/'job.ps';path.write_bytes(b'0123456789'*20)
  try:
   self.assertEqual(ps_job.spool_ps('mock',path),7);self.assertEqual(bytes(stub.data),path.read_bytes());stub.WritePrinter=lambda *a:0
   with self.assertRaises(RuntimeError):ps_job.spool_ps('mock',path)
   self.assertTrue(stub.aborted)
  finally:
   if previous is None:sys.modules.pop('win32print',None)
   else:sys.modules['win32print']=previous
if __name__=='__main__':unittest.main(verbosity=2)
