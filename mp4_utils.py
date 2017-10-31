import click
from copy import copy
import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.colors as colors
import matplotlib.pyplot as plt

#norm=colors.Normalize(vmin=-3, vmax=3))
#norm=colors.Normalize(vmin=0, vmax=21.1048057744))
#norm=colors.Normalize(vmin=0, vmax=4187037.0))
#norm=colors.PowerNorm(gamma=0.2))

def to_mp4(title, oname, frames, data, text=None, fps=10, palette=None, cnorm=None):
  FFMpegWriter = animation.writers['ffmpeg']
  metadata = dict(title=title, artist='mp4 video maker',
                  comment=title)
  if palette is None:
    palette = copy(plt.cm.viridis)
    palette.set_over('r', 1.0)
    palette.set_under('g', 1.0)
    palette.set_bad('k', 1.0)

  writer = FFMpegWriter(fps=10, metadata=metadata)
  fig = plt.figure(figsize=(8, 4))
  ax1 = plt.axes(frameon=False)
  ax1.axes.get_yaxis().set_visible(False)
  ax1.axes.get_xaxis().set_visible(False)
  plt.tight_layout()
  plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
  for spine in ax1.spines.itervalues():
    spine.set_visible(False)
  if cnorm is None:
    cnorm = colors.Normalize(vmin=0, vmax=1)
  img = plt.imshow(data, cmap=palette, norm=cnorm)
  if text:
    text = plt.text(0.5, 0.1, '', ha = 'center', va = 'center',
                    color='y', fontsize=24, transform = ax1.transAxes)

  with writer.saving(fig, oname, 180):
    with click.progressbar(range(frames), length=frames) as bar:
      for i in bar:
        yield i, img, text
        writer.grab_frame()
