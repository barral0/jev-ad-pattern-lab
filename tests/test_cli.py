import unittest, tempfile, subprocess, sys, os, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CliTests(unittest.TestCase):
    def test_help_doctor_and_import_commands(self):
        cli=ROOT/'scripts/lab.py'
        result=subprocess.run([sys.executable,str(cli),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('import-json',result.stdout)
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(cli),'--data-dir',d,'doctor'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout); self.assertIn(report['api_key'],['configured','missing'])
            capture=Path(d)/'synthetic.json'; capture.write_text(json.dumps([{'ad_id':'1','page_id':'9','copy':'SYNTHETIC import'}]))
            result=subprocess.run([sys.executable,str(cli),'--data-dir',d,'import-json',str(capture),'--page-id','9'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['imported_ads'],1)
    def test_dotenv_does_not_override_environment(self):
        from scripts.lab import load_env
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'.env'; file.write_text('TYPESAFE_API_KEY="SYNTHETIC local"\nOTHER=ignored\n')
            old=os.environ.get('TYPESAFE_API_KEY')
            try:
                os.environ['TYPESAFE_API_KEY']='SYNTHETIC external';load_env(file)
                self.assertEqual(os.environ['TYPESAFE_API_KEY'],'SYNTHETIC external')
                del os.environ['TYPESAFE_API_KEY'];load_env(file)
                self.assertEqual(os.environ['TYPESAFE_API_KEY'],'SYNTHETIC local')
            finally:
                if old is None: os.environ.pop('TYPESAFE_API_KEY',None)
                else: os.environ['TYPESAFE_API_KEY']=old
