import numpy as np, sounddevice as sd, soundfile as sf
class Recorder:
    def __init__(self, device=None, rate=44100):
        self.device, self.rate, self.chunks, self.stream = device, rate, [], None
    def start(self):
        self.chunks=[]
        def cb(indata, frames, time_info, status): self.chunks.append(indata.copy())
        self.stream=sd.InputStream(device=self.device, samplerate=self.rate, channels=1, dtype='float32', callback=cb)
        self.stream.start()
    def stop(self, path):
        self.stream.stop(); self.stream.close()
        audio=np.concatenate(self.chunks) if self.chunks else np.zeros((0,1),dtype=np.float32)
        sf.write(str(path),audio,self.rate,subtype='PCM_24')
        return len(audio)/self.rate
def tone(freq=440, duration=.25, rate=44100):
    x=np.arange(int(rate*duration))/rate
    sd.play((.2*np.sin(2*np.pi*freq*x)).astype('float32'),rate)
