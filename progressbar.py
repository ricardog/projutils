from itertools import cycle
import sys
import time

class ProgressBar(object):
  '''Class to display progress bar.
  '''
  def __init__(self, maximum, barLength):
    '''Init progressbar instance.

    @param maximum    maximum progress value
    @param barLength  length of the bar in characters
    '''
    self.maxValue = maximum
    self.barLength = barLength
    self.spin = cycle(r'-\|/').next
    self.lastLength = 0
    self.tmpl = '%-' + str( barLength ) + 's ] %c %5.1f%%'
    self.start = time.time()
    sys.stdout.write( '[ ' )
    sys.stdout.flush()

  def update(self, value):
    '''Update progressbar.

    @param value    Input new progress value
    '''
    # Remove last state.
    sys.stdout.write( '\b' * self.lastLength )

    percent = value * 100.0 / self.maxValue
    # Generate new state
    width = int( percent / 100.0 * self.barLength )
    output = self.tmpl % ( '-' * width, self.spin(), percent )

    # Show the new state and store its length.
    sys.stdout.write( output )
    sys.stdout.flush()
    self.lastLength = len( output )

  def done(self):
    '''Called to print a new line and (optionally) the time elapsed for the
operation.
    '''
    print '\nCompleted in %.2fs' % (time.time() - self.start)
    
