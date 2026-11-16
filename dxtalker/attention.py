"""Short generated attention sounds, serialized with the spot announcement."""
from array import array
import math
import sys
from .audio import Clip

SOUNDS = ('Off', 'Double ding', 'Chime', 'Beep')


def alert_clip(kind, rate=22050, channels=1):
    if kind not in SOUNDS or kind == 'Off':
        raise ValueError('Choose Double ding, Chime or Beep to preview a sound')
    notes = ((880, .18), (880, .18)) if kind == 'Double ding' else ((660, .12), (880, .12), (1108, .18)) if kind == 'Chime' else ((880, .15),)
    samples = array('h')
    for frequency, duration in notes:
        for n in range(round(rate * duration)):
            t = n / rate
            envelope = min(1, t / .008) * (math.exp(-12 * t) if kind != 'Beep' else min(1, (duration - t) / .01))
            value = round(7000 * envelope * (math.sin(2 * math.pi * frequency * t) + .25 * math.sin(4 * math.pi * frequency * t)))
            samples.extend([value] * channels)
        samples.extend([0] * (round(rate * .08) * channels))
    if sys.byteorder != 'little': samples.byteswap()
    return Clip(samples.tobytes(), rate, channels)


def prepend_alert(clip, kind):
    alert = alert_clip(kind, clip.rate, clip.channels)
    return Clip(alert.pcm + clip.pcm, clip.rate, clip.channels)
