import sys
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from forensics.video import decode,QualityExclusion
import index16_decode


class Index16Tests(unittest.TestCase):
    def test_short_but_complete_native_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'16frames_10fps.avi'
            w=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'FFV1'),10,(64,64))
            self.assertTrue(w.isOpened())
            for i in range(16):w.write(np.full((64,64,3),30+i*8,dtype=np.uint8))
            w.release();cfg={'frames':16,'fps':8,'window_sec':2,'size':64}
            with self.assertRaises(QualityExclusion):decode(path,cfg)
            frames,q=index16_decode.decode(path,cfg)
            self.assertEqual(frames.shape,(16,64,64,3));self.assertEqual(q['indices'],list(range(16)))
            self.assertAlmostEqual(q['duration'],1.6,places=3)
            self.assertEqual(len({f.tobytes() for f in frames}),16)


if __name__=='__main__':unittest.main()
