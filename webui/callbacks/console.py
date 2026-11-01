from sys import stdout, stderr

from dash import Input, Output, callback, html
from dash.exceptions import PreventUpdate

from ..state import colorAnsi, vs

class StdoutIntercept(object):
    """
    alive-progress stdout :

    'Remain to progress : 2002/3673'
    '\n'
    '\x1b[?25l'
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▁▃▅'
    ' '
    '1671/3673 [45%] '
    'in 0s '
    '(~0s, 0.0/s) '
    ''
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▂▄▆'
    ' '
    '1671/3673 [45%] '
    'in 0s '
    '(~0s, 0.0/s) '
    ''
    '\x1b[2K\r'
    '\x1b[J'
    'on 1673: Took : 0:00:04.991'
    '\n'
    '\x1b[2K\r'
    '\x1b[J'
    'on 1671: \x1b[31mProcess stoped\x1b[0m'
    '\n'
    '\r'
    '|██████████████████▎                     |'
    ' '
    '▂▂▄'
    ' '
    '1671/3673 [45%] '
    'in 1s '
    '(~0s, 0.0/s) '
    ''
    '\x1b[?25h'
    '\x1b[J'
    '\r'
    '|██████████████████▎⚠︎                    |'
    ' '
    '(!) 1671/3673 [45%] '
    'in 1.5s '
    '(0.00/s) '
    '\x1b[K'
    ''
    '\n'
    'SUMMARY :'
    ''
    '\n------------------------------------'

    """
    def __init__(self):
        self.stdoutW = stdout.write
        self.stderrW = stderr.write
        stdout.write = self.write
        stderr.write = self.write

        self.queueLines = ['']
        self.QUEUE_LIMIT = 512
        # min
        if self.QUEUE_LIMIT < 256:
            self.QUEUE_LIMIT = 256

        self.AP_ANSI_ESCAPE_CODE = [
            '\x1b[?25l',
            # it appears as '\x1b[2K\r' before 'on xxxx:' line
            '\x1b[2K',
            '\x1b[J',
            '\x1b[?25h',
            '\x1b[K',
        ]

    def __del__(self):
        stdout.write = self.stdoutW
        stderr.write = self.stderrW

    def write(self, msg:str):
        self.stdoutW(msg)

        # skip ANSI Escape Code
        if msg in self.AP_ANSI_ESCAPE_CODE:
            return
        
        self.queueLines[-1] += msg

        if msg == '\n':
            self.queueLines.append('')
        elif msg == '\r':
            self.queueLines[-1] = ''
        # elif ('\n' in msg) and ('\r' in msg):
        # elif '\n' in msg:
        elif '\r' in msg:
            self.queueLines[-1] = msg.split('\r')[-1]
        
        # limit queue size
        if len(self.queueLines) > self.QUEUE_LIMIT:
            # remove first 50 element
            del self.queueLines[:50]
        
stdout = StdoutIntercept()

@callback(
    Output('div_processRunning', 'children'),
    Input('interval_log', 'n_intervals'),
)
def logConsole(_):
    global stdout, colorAnsi

    # skip if no stdout
    if stdout.queueLines == ['']:
        raise PreventUpdate
    
    children = []
    queueLines = stdout.queueLines
    
    # represent queue line
    for queueLine in queueLines[::-1]:
        hasAnsiColor = False
        # check if has ansi color code
        for color, ansi in colorAnsi.items():
            if ansi in queueLine:
                hasAnsiColor = True
                # remove ansi color code
                queueLine = queueLine.replace(ansi, "")
                if color != "reset":
                    children.append(html.Span(
                        queueLine,
                        style={"color":color}
                    ))
        # no color append
        if not hasAnsiColor:
            children.append(html.Span(queueLine))

    return children



@callback(
    Output('input_path', 'value'),
    Input('interval_log', 'disabled'),
)
def loadPageRefresh(_):
    global vs
    return vs.path
