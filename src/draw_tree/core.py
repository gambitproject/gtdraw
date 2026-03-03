"""
Game tree drawing as TikZ file from .ef file

This module provides functionality to generate TikZ code for game trees
from extensive form (.ef) files, with support for Jupyter notebooks.
"""
from __future__ import annotations

import sys
import math
import subprocess
import tempfile
import re
from typing import TYPE_CHECKING

from numpy import save

if TYPE_CHECKING:
    import pygambit

from pathlib import Path
from typing import List, Optional 
from IPython.core.getipython import get_ipython

from draw_tree.layout import DefaultLayout

# Constants
DEFAULTFILE: str = "example.ef"
scale: float = 1
grid: bool = False

maxplayer: int = 4
payup: float = 0.1   # fraction of paydown to shift first payoff up
radius: float = 0.3   # iset radius

# Up to 4 players and chance (in principle more)
# Default names
playername: List[str] = [r"\small chance", "1", "2", "3", "4"]
playertexname: List[str] = ["playerzero", "playerone", "playertwo", "playerthree", "playerfour"]
# Player names that need to be defined in TeX
playerdefined: List[bool] = [False] * (maxplayer + 1)

# TikZ/TeX constants used, defined in TeX file, not here
paydown: str = "\\paydown"  # 2.5ex % yshift payoffs down
yup: str = "\\yup"  # 0.5mm % yshift up for moves
yfracup: str = "\\yfracup"  # 0.8mm % yshift up for chance probabilities
spx: str = "\\spx"  # 1mm % single player node xshift
spy: str = "\\spy"  # .5 mm % single player node yshift
ndiam: str = "\\ndiam"  # 1.5mm % node diameter disks
sqwidth: str = "\\sqwidth"  # 1.6 mm % node diameter disks
thickn: str = "line width=\\treethickn"  # {1pt} % line thickness

# Add a global dictionary to track node-to-player mappings from isets
node_to_iset_player: dict[str, int] = {}

numepsilon: float = 1e-9  # checking for almost equality

# Parameters for info set drawings
isetparams: str = ""  # draw parameters for info set drawings

# All dimensions in cm
isetradius: float = 0.3
# Elongated single iset in which direction
xsingleiset: float = 0.4
ysingleiset: float = 0.0

# How to indent
joinstring: str = "\n    "

# Output routines
allowcomments: bool = True

outstream: List[str] = []
stream0: List[str] = []



GAMBIT_MAX_PLAYER = 6
MAX_COLOR_SCHEME_PLAYERS = 7  

_distinctipy_n: int = MAX_COLOR_SCHEME_PLAYERS

_DISTINCTIPY_FALLBACK_RGB = [
    (117, 145, 56),   (234, 51, 35),   (0, 102, 204),  (255, 140, 0),
    (128, 0, 128),    (0, 191, 255),   (255, 0, 255),
]


def _get_distinctipy_colors(n: int) -> list[tuple[int, int, int]]:
    """Return n distinct RGB tuples (0-255). Use distinctipy if available, else fallback."""
    try:
        import distinctipy  
        colors_01 = distinctipy.get_colors(n)
        return [
            (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
            for (r, g, b) in colors_01
        ]
    except ImportError:
        return [_DISTINCTIPY_FALLBACK_RGB[i % len(_DISTINCTIPY_FALLBACK_RGB)] for i in range(n)]


def get_player_color(player: int, color_scheme: Optional[str] = "default") -> str:
    """
    Get the TeX color macro name for a given player number.

    Args:
        player: Player number (1-6 for regular players).
        color_scheme: Optional color scheme name.

    Returns:
        TeX color macro name for the player, or "black" as fallback.
    """
    if color_scheme == "gambit":
        # Color mapping for up to 6 players
        color_map = {
            0: "\\chancecolor",
            1: "\\playeronecolor",
            2: "\\playertwocolor",
            3: "\\playerthreecolor",
            4: "\\playerfourcolor",
            5: "\\playerfivecolor",
            6: "\\playersixcolor",
        }

        return color_map.get(player, "black")
    if color_scheme == "distinctipy":
        if 0 <= player < _distinctipy_n:
            return f"distinct{player}"
        return "black"

    return "black"


def color_definitions(color_scheme: Optional[str] = "default", n: Optional[int] = None) -> list[str]:
   
    global _distinctipy_n
 
    if color_scheme == "gambit":
    
        return [
            "\\definecolor{chancecolorrgb}{RGB}{117,145,56}",
            "\\definecolor{gambitredrgb}{RGB}{234,51,35}",
            "\\newcommand\\chancecolor{chancecolorrgb}",
            "\\newcommand\\playeronecolor{gambitredrgb}",
            "\\newcommand\\playertwocolor{blue}",
            "\\newcommand\\playerthreecolor{orange}",
            "\\newcommand\\playerfourcolor{purple}",
            "\\newcommand\\playerfivecolor{cyan}",
            "\\newcommand\\playersixcolor{magenta}",
        ]
    if color_scheme == "distinctipy":
       
        num_colors = min(n if n is not None and n > 0 else MAX_COLOR_SCHEME_PLAYERS, MAX_COLOR_SCHEME_PLAYERS)
        _distinctipy_n = num_colors
        colors_rgb = _get_distinctipy_colors(num_colors)
        return [
            f"\\definecolor{{distinct{i}}}{{RGB}}{{{r},{g},{b}}}"
            for i, (r, g, b) in enumerate(colors_rgb)
        ]
    return []

def outall(stream: Optional[List[str]] = None) -> None:
    """
    Output stream to stdout.
    
    Args:
        stream: List of strings to output. Defaults to global outstream.
    """
    if stream is None:
        stream = outstream
    for s in stream:
        print(s)


def outs(s: str, stream: Optional[List[str]] = None) -> None:
    """
    Output single string to stream.
    
    Args:
        s: String to append to stream.
        stream: Target stream list. Defaults to global outstream.
    """
    if stream is None:
        stream = outstream
    stream.append(s)


def outlist(string_list: List[str]) -> None:
    """
    Output list of strings to global outstream.
    
    Args:
        string_list: List of strings to append to global outstream.
    """
    global outstream
    outstream += string_list


def defout(defname: str, meaning: str) -> None:
    """
    LaTeX command for defining something.
    
    Args:
        defname: Name of the definition.
        meaning: Value/meaning of the definition.
        
    Note:
        Outputs TeX definition. Consider changing to LaTeX \\newcommand*.
    """
    outs("\\def\\" + defname + "{" + meaning + "}")


def newdimen(dimname: str, value: str) -> None:
    """
    LaTeX command for creating a dimension.
    
    Args:
        dimname: Name of the dimension.
        value: Value of the dimension.
    """
    outs("\\newdimen\\" + dimname)
    outs("\\" + dimname + value)


def comment(s: str) -> None:
    """
    Output comment if not suppressed.
    
    Args:
        s: Comment text to output.
    """
    if allowcomments:
        outs("%% " + s)


def error(s: str, stream: Optional[List[str]] = None) -> None:
    """
    Output error message (errors not suppressed).
    
    Args:
        s: Error message text.
        stream: Target stream. Defaults to global outstream.
    """
    if stream is None:
        stream = outstream
    outs("% ----- Error: " + s, stream)

def readfile(filename: str) -> List[str]:
    """
    Read file lines, stripped of blanks at end, if non-empty, into list.
    
    Args:
        filename: Path to file to read.
        
    Returns:
        List of non-empty, stripped lines from the file.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        
    Reference:
        http://stackoverflow.com/questions/12330522/reading-a-file-without-newlines
    """
    with open(filename, 'r') as file:
        temp = file.read().splitlines()
    out = []
    for line in temp:
        line = line.strip()
        if line:
            out.append(line)
    return out


def get_max_player_index_from_ef(ef_file: str) -> int:
    """
    Scan an .ef file and return the maximum player index (0 = chance, 1+ = players).
    Used to determine how many distinct colors to generate for the distinctipy scheme.
    """
    lines = readfile(ef_file)
    max_player = 0
    for line in lines:
        if line.startswith('%') or line.startswith('#'):
            continue
        parts = line.split()
        for i, word in enumerate(parts):
            if word == "player" and i + 1 < len(parts) and parts[i + 1].isdigit():
                max_player = max(max_player, int(parts[i + 1]))
                break
    return max_player


def fformat(x: float, places: int = 3) -> str:
    """
    Format float to specified places, remove trailing ".0".
    
    Args:
        x: Number to format.
        places: Number of decimal places (default: 3).
        
    Returns:
        Formatted string representation of the number.
        
    Examples:
        >>> fformat(3.14159)
        '3.142'
        >>> fformat(3.0)
        '3'
        >>> fformat(3.100, 2)
        '3.1'
        >>> fformat(0.5000000)
        '0.5'
    """
    fstring = "%." + ("%df" % places)
    s = fstring % x
    if places > 0:
        s = s.rstrip("0")
        s = s.rstrip(".")
    return s


def coord(x: float, y: float) -> str:
    """
    Format coordinates as pair: 3,4 -> "(3,4)".
    
    Args:
        x: X coordinate.
        y: Y coordinate.
        
    Returns:
        Formatted coordinate string.
        
    Examples:
        >>> coord(1.0, 2.0)
        '(1,2)'
    """
    return "(" + fformat(x) + "," + fformat(y) + ")"


def twonorm(v: List[float]) -> float:
    """
    Calculate Euclidean length of vector.
    
    Args:
        v: Vector as list of coordinates.
        
    Returns:
        Euclidean length of the vector.
        
    Examples:
        >>> twonorm([3, 4])
        5.0
    """
    length = 0.0
    for x in v:
        length += x**2
    return length**0.5


def stretch(v: List[float], length: float = 1) -> List[float]:
    """
    Stretch vector to desired length (must be >= 0).
    
    Args:
        v: Input vector.
        length: Desired length (default: 1).
        
    Returns:
        Stretched vector with specified length.
        
    Raises:
        AssertionError: If the result doesn't have the expected length.
    """
    currl = twonorm(v)
    if currl == 0.0:
        return v
    out = []
    for x in v:
        out.append(x * length / currl)
    assert aeq(twonorm(out), length)
    return out


def degrees(v: List[float]) -> float:
    """
    Calculate angle of vector in degrees in (-180,180].
    
    Args:
        v: Vector as list of coordinates.
        
    Returns:
        Angle in degrees.
    """
    currl = twonorm(v)
    if aeq(currl):
        return 0
    onunitcircle = stretch(v)
    x = onunitcircle[0]
    y = onunitcircle[1]
    xd = math.acos(x) * 180 / math.pi
    if y < 0:
        return -xd  # in (-180,0)
    return xd  # in [0,180]


def aeq(x: float, y: float = 0) -> bool:
    """
    Test if numbers are almost equal (or equal to zero) numerically.
    
    Args:
        x: First number.
        y: Second number (default: 0).
        
    Returns:
        True if numbers are approximately equal.
    """
    return abs(x - y) < numepsilon


def det(a: float, b: float, c: float, d: float) -> float:
    """
    Calculate determinant of 2x2 matrix.
    
    Args:
        a, b, c, d: Matrix elements [[a, b], [c, d]].
        
    Returns:
        Determinant value (ad - bc).
    """
    return a * d - b * c

def isonlineseg(a: List[float], b: List[float], c: List[float]) -> bool:
    """
    Check if point b lies on the line segment [a,c].
    
    Args:
        a: Starting point as [x, y] coordinates.
        b: Point to test as [x, y] coordinates.
        c: Ending point as [x, y] coordinates.
        
    Returns:
        True if point b is on the line segment from a to c, False otherwise.
    """
    bx=b[0]-a[0]
    by=b[1]-a[1]
    cx=c[0]-a[0]
    cy=c[1]-a[1]
    if aeq(bx) and aeq(by):
        return True  # a near b
    if aeq( bx*cy - by*cx ): # collinear
        if aeq(cx) and aeq(cy) : # a near c but not near b
            return False
        if aeq(cx): # look at y coordinate
            if aeq(by,cy):
                return True  # c near b 
            if cy >= 0:
                return (by >= 0) and (by <= cy)
            # cy < 0
            return (by <= 0) and (by >= cy)
        # nonzero x coordinate of c, gives info
        if aeq(bx,cx):
            return True  # c near b 
        if cx > 0:
            return (bx >= 0) and (bx <= cx)
        # cx < 0
        return (bx <= 0) and (bx >= cx)
    # not collinear
    return False

def makearc(a: List[float], b: List[float], c: List[float], radius: float = isetradius) -> str:
    """
    Create arc or point around point b in triangle a,b,c.
    
    Args:
        a: First point as [x, y] coordinates.
        b: Center point as [x, y] coordinates.
        c: Third point as [x, y] coordinates.
        radius: Radius for the arc. Defaults to isetradius.
        
    Returns:
        TikZ coordinate string for the arc or point.
    """
    s = stretch([ b[1]-a[1], a[0]-b[0] ], radius)
    t = stretch([ c[1]-b[1], b[0]-c[0] ], radius)
    # print "% s,t    ", s,t
    sangle = degrees(s)
    tangle = degrees(t)
    # make sure to turn anticlockwise
    if tangle < sangle:
        tangle += 360
    sx = b[0] + s[0]
    sy = b[1] + s[1]
    # tikz code
    out = coord(sx,sy) + " arc("
    out += fformat(sangle,1) + ":"
    out += fformat(tangle,1) + ":"
    out += fformat(radius) + ")"
    # checking if point rather than arc
    # print "%  tangle-sangle ", tangle-sangle 
    if tangle-sangle > 180.01:
        tx = b[0] + t[0]
        ty = b[1] + t[1]
        if tangle-sangle > 359: # very close to straight
            # print "% 359"
            x=(sx+tx)/2
            y=(sy+ty)/2
            out = coord(x,y)
        else:
            ax = a[0] + s[0]
            ay = a[1] + s[1]
            cx = c[0] + t[0]
            cy = c[1] + t[1]
            # print "% sx,sy,tx,ty", sx,sy,tx,ty
            # print "% ax,ay,cx,cy", ax,ay,cx,cy
            D = det (sx-ax,sy-ay,cx-tx,cy-ty)
            if not aeq(D):  # zero determinant - do nothing
                alpha = det(cx-ax,cy-ay,cx-tx,cy-ty) / D
                beta  = det(sx-ax,sy-ay,cx-ax,cy-ay) / D
                # print "% alpha ", alpha
                # print "% beta  ", beta
                assert (alpha<1)
                assert (beta<1)
    ## trying to salvage tight angles, other solution is better
    #           if alpha<0:
    #               x = ax
    #               y = ay
    #           elif beta<0:
    #               x = cx
    #               y = cy
    #           else :
    #               x = ax + (sx-ax)*alpha
    #               y = ay + (sy-ay)*alpha
    #           out = coord(x,y)
                if alpha >= 0 and beta >= 0 :
                    x = ax + (sx-ax)*alpha
                    y = ay + (sy-ay)*alpha
                    out = coord(x,y)
    return out 

def arcseq(nodes: List[List[float]], radius: float = isetradius) -> List[str]:
    """
    Create a list of TikZ drawing commands around a list of coordinate pairs.
    
    Creates a sequence of arcs around the given nodes, removing collinear points
    and handling singleton information sets appropriately.
    
    Args:
        nodes: List of coordinate pairs [x,y].
        radius: Radius for the arcs. Defaults to isetradius.
        
    Returns:
        List of TikZ command strings (without "draw" and ";" wrapper).
    """ 
    nodes = nodes[:] # protect nodes parameter, now a local variable
    if len(nodes) == 0:
        return [""]
    if len(nodes) == 1: # singleton info set
        x = nodes[0][0]
        y = nodes[0][1]
        # circle only?
        if aeq(xsingleiset) and aeq(ysingleiset): # no offset
            # tikz code 
            s = coord(x,y) + " circle [radius="
            s += fformat(radius) + "cm]"
            return [s]
        # else extend with extra point
        else: 
            nodes.append([x+xsingleiset,y+ysingleiset])
    # now at least length 2
    # successively remove points on same line segment
    a = nodes.pop(0)
    b = nodes.pop(0)
    newnodes = [a]
    while (nodes):
        c = nodes.pop(0)
        if not isonlineseg(a,b,c):
            newnodes.append(b)
            a = b
        b=c
    newnodes.append(b)
    tour = newnodes[1:2]+newnodes[:-1]+newnodes[::-1]
    out = []
    for i in range(1, len(tour)-1):
        out.append(makearc(tour[i-1],tour[i],tour[i+1],radius))
    return out  

def iset(nodes: List[List[float]], radius: float = isetradius) -> str:
    """
    Create complete TikZ drawing commands for an information set.
    
    Args:
        nodes: List of coordinate pairs [x,y].
        radius: Radius for the arcs. Defaults to isetradius.
        
    Returns:
        Complete TikZ draw command string with semicolon.
    """ 
    arcs = arcseq(nodes,radius)
    # tikz code 
    return "\\draw [" + isetparams + "] " + "\n  -- ".join(arcs) + " -- cycle;"

######################## handling players

def player(words: List[str]) -> tuple[int, int]:
    """
    Parse 'player' command and handle player definitions.
    
    Processes player number and optional name, writing out player definition
    if the player is named or used for the first time.
    
    Args:
        words: List of command words starting with 'player'.
        
    Returns:
        Tuple of (player_number, advance_count) where advance_count is 
        the number of words consumed from the input.
    """
    p = -1  # illegal player
    advance = len(words)
    assert words[0] == "player"
    try:
        x = int(words[1])
    except ValueError:
        error("need player number after 'player'")
        return p, advance
    if x < 0 or x > maxplayer:
        error("need player number in 0.."+str(maxplayer)+" after 'player'")
        advance = 2 # allow continued processing
        return p, advance
    p = x
    if len(words) > 2:
        if words[2] == "name":
            if len(words) == 3: # nothing there
                error("player name needed after 'name'")
                return p, advance
            playername[p] = words[3] # got new player name
            playerdefined[p] = False
            advance = 4
        else:
            advance = 2 # only "player p" parsed
    if not playerdefined[p]:
        defout(playertexname[p], playername[p])
        playerdefined[p] = True
    return p, advance

######################## handling nodes

# each node is itself a dict, with the fields
# "x", "y", "player", "from", "move", "xshift"

nodes = {}
xshifts = {}

def splitnumtext(s: str) -> tuple[float, str]:
    """
    Split a string into numeric prefix and text remainder.
    
    Extracts a leading number (including decimal) from a string and returns
    both the number and the remaining text.
    
    Args:
        s: Input string to parse.
        
    Returns:
        Tuple of (number, remainder_text). If no number is found, 
        returns (1, original_string).
        
    Examples:
        "2.3abc" -> (2.3, "abc")
        ".1b" -> (0.1, "b") 
        "a" -> (1, "a")
    """
    nodotyet = True
    tonum = ""
    remainder = ""
    for i in range(len(s)):
        c = s[i]
        if nodotyet and c == ".":
            nodotyet = False
            tonum += c
        elif c.isdigit():
            tonum += c
        else:
            remainder = s[i:]
            break
    if tonum and tonum != ".":
        return float(tonum), remainder
    return 1, remainder
    ## testing:
    # a = ["2.3abc", ".1b", ".4...f", ".4s1", "22.2xyz)", "a"]
    # for s in a:
    #     print s, splitnumtext(s)
    # quit()

def xshift(words: List[str]) -> tuple[float, float, int]:
    """
    Parse 'xshift' command to determine horizontal positioning.
    
    Handles xshift assignments and lookups, including named xshift variables
    and coefficient multipliers.
    
    Args:
        words: List of command words starting with 'xshift'.
        
    Returns:
        Tuple of (x_shift, factor, advance_count) where:
        - x_shift: The calculated horizontal shift value
        - factor: The coefficient factor for scaling
        - advance_count: Number of words consumed (always 2)
    """
    assert words[0] == "xshift"
    xs = 0
    advance = len(words)
    if len(words) < 2:
        error("need specification after 'xshift'")
        return xs, 1, advance
    s = words[1]
    # negative slope?
    neg = s[0] == "-"
    if neg:
        s = s[1:]
    # is there an assignment taking place?
    a = s.split("=")
    assignment = len(a) > 1
    if assignment:
        try:
            num = float(a[1])
        except ValueError:
            error("assigment '"+ a[1] + "' must be a number")
            return xs, 1, advance
        coeff, xsname = splitnumtext(a[0])
        if xsname in xshifts:
            comment("Warning: xshift '" + xsname + \
                "' re-defined to "+str(num))
        xshifts[xsname] = num
        num *= coeff
    else:
        coeff, xsname = splitnumtext(a[0])
        if xsname: # uses a name
            if xsname not in xshifts:
                error("xshift '" + xsname + "' undefined")
                return xs, 1, advance
            num = coeff * xshifts[xsname]
        else:
            num = coeff
            coeff = 1 # no use of factor without label
    if aeq(num): # nearly zero
        xs = 0
        if aeq(coeff): # coefficient nearly zero
            factor = 1
        else:
            factor = coeff
    else: # num nonzero and therefore coeff nonzero
        factor = coeff
        if neg:
            xs = -num
        else:
            xs = num
    return xs, factor, 2
    ## testing:
    # a = ["xshift", "-2"]
    # b = ["xshift", "-2a=.3"]
    # c = ["xshift", "3a"]
    # l = [a,b,c]
    # for s in l:
    #     print s, xshift(s)
    #     print outstream
    # quit()

def fromnode(words: List[str]) -> tuple[str, int]:
    """
    Parse 'from' command to identify parent node.
    
    Args:
        words: List of command words starting with 'from'.
        
    Returns:
        Tuple of (parent_node_id, advance_count) where parent_node_id
        is the cleaned node identifier and advance_count is words consumed.
    """
    assert words[0] == "from"
    advance = len(words)
    fromn = ""
    if len(words) < 2:
        error("need node name after 'from'")
        return fromn, advance
    s = cleannodeid(words[1])
    if s not in nodes:
        error("node "+s+" after 'from' is not defined")
    else:
        fromn = s
        advance = 2
    return fromn, advance

def move(words: List[str]) -> tuple[str, str, float, int]:
    """
    Parse 'move' command to extract move name and positioning.
    
    Handles move syntax like "move:Left:0.3" where the colon-separated parts
    specify positioning and convexity parameters.
    
    Args:
        words: List of command words starting with 'move'.
        
    Returns:
        Tuple of (move_name, move_position, convex_value, advance_count).
    """
    assert words[0][:4] == "move"
    advance = len(words)
    mov = ""
    movpos = ""
    convex = -1
    a = words[0].split(":")
    if len(a) > 1:
        movpos = (a[1]+" ")[0].lower() # first character only
    if len(a) > 2:
        try:
            num = float(a[2])
            if num < 0 or num > 1:
                error("Move position in [0,1] required")
            else:
                convex = num
        except ValueError:
            error("Move position in [0,1] required")
    if len(words) < 2:
        error("need move name after 'move'")
        return mov, movpos, convex, advance
    mov = words[1]
    advance = 2
    return mov, movpos, convex, advance

    # # testing
    # l = ["move:Right", "T"]
    # print move (l)
    # outall()
    # quit ("done testing.")

def arrow(words: List[str]) -> tuple[float, str, int]:
    """
    Parse 'arrow' command to extract arrow positioning and color.
    
    Args:
        words: List of command words starting with 'arrow'.
        
    Returns:
        Tuple of (arrow_position, arrow_color, advance_count).
    """
    assert words[0][:5] == "arrow"
    a = words[0].split(":")
    if len(a) > 1:
        arrowcolor = a[1]
    else:
        arrowcolor = ""
    arrowpos = 0.5
    advance = 2  # Default advance value
    try:
        num = float(words[1])
        if num < 0 or num > 1:
            error("Arrow position in [0,1] required, using 0.5")
        else:
            arrowpos = num
    except Exception:
        error("Arrow position in [0,1] required, using 0.5")
    return arrowpos, arrowcolor, advance

def payoffs(words: List[str]) -> List[str]:
    """
    Parse 'payoffs' command to generate TikZ payoff display code.
    
    Args:
        words: List of command words starting with 'payoffs'.
        
    Returns:
        List of TikZ node commands for displaying payoffs.
    """
    assert words[0] == "payoffs"
    maxp = len(words)
    if len(words) > maxplayer+1:
        error("too many payoffs, discard "+str(words[maxplayer+1:]))
        maxp = maxplayer+1
    paylist = []
    for i in range(1, maxp):
        # tikz code
        t = "   node[below,yshift="
        t += fformat(payup-(i-1)) + paydown
        t += "] {$" + words[i]
        if words[i][0] == "-": # negative payoff
            t += "{\\phantom-}"
        t += "$\\strut}"
        paylist.append(t)
    return paylist
    # # testing
    # s = "payoffs -2 3 4 5"
    # s = "payoffs 0 x 1 3 4 5"
    # a = payoffs(s.split())
    # for s in a:
    #     print s
    # quit()

def drawnode(v: List[float], player: int = 1, color_scheme: str = "default") -> str:
    """
    Generate TikZ code to draw a game tree node.
    
    Creates either a square (for chance/player 0) or circle (for other players).
    
    Args:
        v: Node position as [x, y] coordinates.
        player: Player number (0 for chance node, >0 for player node).
        color_scheme: Color scheme for player nodes.
        
    Returns:
        TikZ node command string.
    """
    # tikz code
    out = "\\node[inner sep=0pt,minimum size="
    fillcolor = get_player_color(player, color_scheme)

    # chance nodes
    if player == 0:
        if color_scheme == "default":
            out += sqwidth + ",draw=black,fill="
            out += "red,shape=rectangle] at "
        else:
            out += sqwidth + ",draw=" + fillcolor + ",fill="
            out += fillcolor + ",shape=rectangle] at "
    # player nodes
    else:
        out += ndiam + f", draw={fillcolor}, fill="
        out += fillcolor + ", shape=circle] at "
    out += coord(v[0], v[1]) + " {};"
    outs(out)
    return out

def drawnodes(color_scheme: str = "default") -> None:
    """
    Draw all inner (non-leaf) nodes in the game tree.

    Iterates through all nodes and draws those marked as 'inner' nodes
    using appropriate shapes based on player type.

    This function is called after all edges have been drawn to ensure
    nodes appear on top of edges in the final rendering.

    Args:
        color_scheme: Color scheme for player nodes.
    """
    for nodeid in nodes:
        if nodes[nodeid]["inner"]:
            v = [nodes[nodeid]["x"], nodes[nodeid]["y"]]
            p = nodes[nodeid]["player"]
            drawnode(v, p, color_scheme)

def setnodeid(lev: float, s: str) -> str:
    """
    Create node identifier from level and name.
    
    Args:
        lev: Level number (typically a float).
        s: Name string for the node.
        
    Returns:
        Formatted node identifier string "level,name".
    """
    return fformat(lev)+","+s

def cleannodeid(ns: str) -> str:
    """
    Standardize node id from "level,name" format.
    
    Args:
        ns: Node string in "level,name" format.
        
    Returns:
        Standardized node identifier.
    """
    a = ns.split(",")
    if len(a) < 2:
        error("missing comma in '"+ns+"', using empty node id")
        s = ""
    else:
        s = a[1]
    try:
        lev = float(a[0])
    except Exception:
        error("Level must be a number, using 0")
        lev = 0
    return setnodeid(lev, s)
    # # testing
    # s = "1,2 3,4 .0,r x,7 88 ,"
    # a = s.split()
    # a.append("")
    # for s in a:
    #     print s, cleannodeid(s)
    #     print outstream
    # quit()

# handle "level" keyword;
# commands: "node" node , then in any order
# "xshift" [-][2][[a=]1.5|a]  (2= multiple, a= xshift name, 1.5 = dimen)
# "from" nodeid (nodeid = level,node)
# "move" movename
# "payoffs" list of payoffs, comes last
# "inner" boolean: inner node, draw disk/square

def parse_isets_first(lines: List[str]) -> None:
    """
    Pre-parse all iset commands to build node-to-player mappings.

    This function is called before processing level commands to ensure
    nodes know their player assignment from information sets.

    Args:
        lines: All lines from the .ef file.
    """
    global node_to_iset_player
    node_to_iset_player.clear()

    for line in lines:
        words = line.split()
        if len(words) > 0 and words[0] == "iset":
            p = -1
            count = 1
            nodes_in_iset = []

            # Parse the iset command
            while count < len(words):
                if words[count] == "player":
                    try:
                        p = int(words[count + 1])
                        count += 2
                    except (ValueError, IndexError):
                        count += 1
                else:
                    nodeid = cleannodeid(words[count])
                    nodes_in_iset.append(nodeid)
                    count += 1

            # Map all nodes in this iset to the player
            if p > 0:
                for nodeid in nodes_in_iset:
                    node_to_iset_player[nodeid] = p

def generate_legend(
    player_list: List[int], color_scheme: str = "gambit", scale_factor: float = 1.0
) -> str:
    """
    Generate TikZ code for a color legend showing player colors.

    Args:
        player_list: List of player numbers that appear in the game.
        color_scheme: Color scheme being used.
        scale_factor: The scale factor applied to the main tree (used to adjust spacing).

    Returns:
        TikZ code string for the legend.
    """
    if not player_list or color_scheme == "default":
        return ""

    # Calculate x and y coordinates for legend placement
    min_x = 0
    max_y = 0
    if nodes:
        min_x = min(nodes[nodeid]["x"] for nodeid in nodes)
        max_y = max(nodes[nodeid]["y"] for nodeid in nodes)

    # Position legend in top left corner
    legend_code = "\n% Player color legend\n"
    x_offset = min_x - 1.5
    legend_code += f"\\begin{{scope}}[scale=1,shift={{({x_offset},{max_y})}}]\n"

    # Add each player with their color (no title)
    # Adjust vertical spacing to compensate for the tree's scale factor
    # When tree is scaled down, we need more space in absolute coordinates
    base_spacing = 0.5
    y_spacing = base_spacing / scale_factor
    y_offset = 0

    for player in sorted(player_list):
        if player < 0:
            continue

        player_color = get_player_color(player, color_scheme)
        player_name = playername[player] if player < len(playername) else str(player)

        # Draw colored circle/square
        if player == 0:
            # Chance node - square
            legend_code += f"\\node[inner sep=0pt,minimum size=\\sqwidth,draw={player_color},fill={player_color},shape=rectangle] at (0,{y_offset}) {{}};\n"
        else:
            # Player node - circle
            legend_code += f"\\node[inner sep=0pt,minimum size=\\ndiam,draw={player_color},fill={player_color},shape=circle] at (0,{y_offset}) {{}};\n"

        # Add player label
        legend_code += f"\\node[anchor=west] at (0.3,{y_offset}) {{{player_name}}};\n"

        y_offset -= y_spacing

    legend_code += "\\end{scope}\n"

    return legend_code

def level(
        words: List[str],
        color_scheme: str = "default",
        action_label_position: float = 0.5,
        ) -> None:
    """
    Process a complete level command to create a game tree node.

    This is the main parsing function that handles the 'level' command and all
    its associated sub-commands (player, xshift, from, move, payoffs, arrow).
    Creates TikZ output for drawing the node and connecting lines.

    Args:
        words: List of command words starting with 'level'.
        color_scheme: Color scheme for player nodes.
    """
    assert words[0] == "level"
    try:
        lev = float(words[1])
    except Exception:
        error("Level must be a number")
        return
    try:
        assert words[2] == "node"
    except Exception:
        error("Expected 'node' keyword")
        return
    try:
        s = words[3]
    except Exception:
        error("Expected node name")
        return
    nodeid = setnodeid(lev, s)
    count = 4
    p = -1  # no player yet
    xs = 0  # no xshift yet
    factor = 1  # used for positioning move
    fromn = ""  # no father yet
    mov = ""  # no move yet
    movpos = ""  # no move position (l/r) yet
    convex = -1  # no move position along line yet
    pay = []
    arrowposlist = []
    arrowcolorlist = []
    # process remaining words:
    # xshift, from, player, move, payoffs, arrow
    while count < len(words):
        if words[count] == "player":  # set player
            p, advance = player(words[count:])
            count += advance
        elif words[count] == "xshift":
            xs, factor, advance = xshift(words[count:])
            count += advance
        elif words[count] == "from":
            fromn, advance = fromnode(words[count:])
            count += advance
        elif words[count][:4] == "move":
            mov, movpos, convex, advance = move(words[count:])
            count += advance
        elif words[count][:5] == "arrow":
            arrowpos, arrowcolor, advance = arrow(words[count:])
            arrowposlist.append(arrowpos)
            arrowcolorlist.append(arrowcolor)
            count += advance
        elif words[count] == "payoffs":  # automatically last
            pay = payoffs(words[count:])
            break
        else:  # unknown keyword
            error("unknown keyword " + words[count])
            count += 1
    
    # If move contains a float, apply fformat
    if "~" in mov:
        movlist = mov.split("~")
        try:
            num = float(movlist[1])
            mov = movlist[0] + "~" + str(fformat(num))
        except ValueError:
            pass

    # If no player explicitly assigned, check if this node is in an iset
    node_in_iset = nodeid in node_to_iset_player
    if p < 0 and node_in_iset:
        p = node_to_iset_player[nodeid]

    # now line has been processed, update data from
    # nodeid, p, xs, fromn, move, lev
    # create x coordinate
    existsfrom = fromn in nodes
    xfrom = 0.0  # Initialize to avoid unbound variable warnings
    yfrom = 0.0  # Initialize to avoid unbound variable warnings
    if existsfrom:  # father exists
        xfrom = nodes[fromn]["x"]
        yfrom = nodes[fromn]["y"]
        xx = xfrom + xs
    else:  # no father
        xx = xs
        if fromn:
            error("No 'from' node, move '" + mov + "' ignored")
    # direction down (for later expansion)
    yy = -lev
    nodes[nodeid] = {"x": xx, "y": yy, "player": p}
    nodes[nodeid]["xshift"] = xs
    nodes[nodeid]["move"] = mov
    nodes[nodeid]["from"] = fromn
    # root node always printed
    nodes[nodeid]["inner"] = (pay == []) or (lev == 0)

    # Get player color for styling text labels
    player_color = get_player_color(p, color_scheme)
    color_style = f"color={player_color}"

    # For edges, use the PARENT node's color, not the current node's color
    edge_color_style = ""
    if existsfrom and fromn in nodes:
        parent_player = nodes[fromn]["player"]
        parent_color = get_player_color(parent_player, color_scheme)
        edge_color_style = f"color={parent_color}"

    # tikz code - add color to the draw command for edges based on parent
    s = "\\draw [" + thickn
    if edge_color_style:
        s += "," + edge_color_style
    s += "] " + coord(xx, yy)
    # Only show player label if node is NOT in an information set AND color scheme is default
    # (information sets display their own player labels, and non-default schemes use legend)
    show_label = (
        p >= 0 and playername[p] and not node_in_iset and color_scheme == "default"
    )
    if show_label:
        # default: player to the right of node. perhaps left?
        if existsfrom and xs < 0:
            s += " node[left,xshift=-"
        else:
            s += " node[right,xshift="
        s += spx + ",yshift=" + spy
        if color_style:
            s += "," + color_style
        s += "] {\\"
        s += playertexname[p] + "\\strut}"
    outs(s)
    outlist(pay)  # possibly empty
    if existsfrom:  # draw line to father
        outs("   -- " + coord(xfrom, yfrom) + ";")
        # annotate moves above
        if convex < 0:
            convex = (
                action_label_position / factor
            )
        xmove = xx * convex + xfrom * (1 - convex)
        ymove = yy * convex + yfrom * (1 - convex)
        s = "\\draw " + coord(xmove, ymove)
        # decide if left or right
        if movpos == "r":
            side = "right,xshift=0.0cm"
        elif movpos == "l":
            side = "left,xshift=0.0cm"
        elif xs > 0:  # default
            side = "right"
        else:
            side = "left"
        s += " node[" + side + ",yshift="
        if "frac" in mov:
            s += yfracup
        else:
            s += yup
        # Add edge color to action label
        if edge_color_style:
            s += "," + edge_color_style
        s += "] {$" + mov + "$\\strut};"
        outs(s)
        # output arrows
        while arrowposlist:
            arrowpos = arrowposlist.pop(0)
            arrowcolor = arrowcolorlist.pop(0)
            xtip = xfrom * (1 - arrowpos) + xx * arrowpos
            ytip = yfrom * (1 - arrowpos) + yy * arrowpos
            xback = xfrom * (1.01 - arrowpos) + xx * (arrowpos - 0.01)
            yback = yfrom * (1.01 - arrowpos) + yy * (arrowpos - 0.01)
            if not arrowcolor == "":
                arrowcolor = "[fill=" + arrowcolor + "]"
            s = "\\draw [-{StealthFill" + arrowcolor + "}]"
            s += coord(xback, yback)
            s += " -- " + coord(xtip, ytip) + ";"
            outs(s)
    else:
        outs("   ;")
    return

######################## isets

def isetgen(words: List[str], color_scheme: str = "default") -> None:
    """
    Process 'iset' command to generate information set visualization.

    Creates TikZ code to draw information sets (connecting multiple nodes
    that belong to the same player and decision point).

    Args:
        words: List of command words starting with 'iset'.
        color_scheme: Color scheme for player nodes.
    """
    global isetparams
    assert words[0] == "iset"
    nodelist = []
    p = -1
    count = 1
    where = 0  # where "player" was found
    while count < len(words):
        if words[count] == "player":
            p, advance = player(words[count:])
            where = count
            count += advance
        else:
            nodeid = cleannodeid(words[count])
            if nodeid not in nodes:
                error(" ".join(words) + " :", stream0)
                error("Node '" + nodeid + "' in iset not defined", stream0)
            else:
                v = [nodes[nodeid]["x"], nodes[nodeid]["y"]]
                nodelist.append(v)
            count += 1
    # generate and ship iset
    if len(nodelist) == 0:
        error(" ".join(words) + " :", stream0)
        error("No valid nodes in iset", stream0)
        return

    # Set isetparams to use player color if player is defined
    if p > 0:
        player_color = get_player_color(p, color_scheme)
        isetparams = f"color={player_color}"
    else:
        isetparams = ""

    outs(iset(nodelist, radius / scale), stream0)

    # Reset isetparams after drawing
    isetparams = ""

    # Only show player labels for information sets if using default color scheme
    if p >= 0 and playername[p] and color_scheme == "default":
        # Get player color for styling
        player_color = get_player_color(p, color_scheme)
        color_style = f"color={player_color}"

        if len(nodelist) == 1:
            n = nodelist[0]
            # tikz code
            s = "\\draw " + coord(n[0], n[1])
            # player to the right of node (for later expansion)
            s += " node[right,xshift="
            s += spx + ",yshift=" + spy
            if color_style:
                s += "," + color_style
            s += "] {\\"
            s += playertexname[p] + "} ;"
            outs(s)
        else:  # at least two nodes
            if where > len(nodelist):  # "player" at end
                where = int(len(nodelist) / 2) + 1
            if where < 2:
                where = 2
            n1 = nodelist[where - 2]
            n2 = nodelist[where - 1]
            # tikz code
            s = "\\draw "
            s += coord((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2)
            s += " node[xshift=0.0cm"
            if color_style:
                s += "," + color_style
            s += "] {\\" + playertexname[p] + "} ;"
            outs(s)
    return

########### command-line arguments

def commandline(argv: List[str]) -> tuple[str, bool, bool, bool, Optional[str], Optional[int], str]:
    """
    Process command-line arguments to set global configuration.
    
    Sets global variables for ef_file, scale, and grid based on
    command-line arguments. Also detects if PDF or PNG output is requested.
    
    Args:
        argv: List of command-line arguments (including script name).
        
    Returns:
        Tuple of (output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi,color_scheme) where:
        - output_mode: 'tikz', 'pdf', 'png', or 'tex'
        - pdf_requested: True if --pdf flag was provided
        - png_requested: True if --png flag was provided
        - tex_requested: True if --tex flag was provided
        - output_file: Custom output filename if specified
        - dpi: DPI setting for PNG output (None if not specified)
        - color_scheme: Color scheme for player nodes (default, gambit, distinctipy)
    """
    global grid
    global scale
    global ef_file
    
    pdf_requested = False
    png_requested = False
    tex_requested = False
    output_file = None
    dpi = None
    color_scheme = "default"
    
    for arg in argv[1:]:
        if arg[:5] == "scale":
            a = arg.split("=")
            try:    
                num = float(a[1])
                if num >= 0.01 and num <= 100:
                    scale = num
                else: 
                    outs("% Command-line argument 'scale=x' needs x in 0.01 .. 100", stream0)
            except Exception:
                outs("% Command-line argument 'scale=x' needs x in 0.01 .. 100", stream0)
        elif arg == "grid":
            grid = True
        elif arg == "--pdf":
            pdf_requested = True
        elif arg == "--png":
            png_requested = True
        elif arg == "--tex":
            tex_requested = True
        elif arg.startswith("--output="):
            output_file = arg[9:]  # Remove "--output=" prefix
            if output_file.endswith('.pdf'):
                pdf_requested = True
            elif output_file.endswith('.png'):
                png_requested = True
            elif output_file.endswith('.tex'):
                tex_requested = True
        elif arg.startswith("--dpi="):
            try:
                dpi = int(arg[6:])  # Remove "--dpi=" prefix
                if dpi < 72 or dpi > 2400:
                    print("Warning: DPI should be between 72 and 2400, using default 300", file=sys.stderr)
                    dpi = 300
            except ValueError:
                print("Warning: Invalid DPI value, using default 300", file=sys.stderr)
                dpi = 300
        elif arg.startswith("--color-scheme="):
            color_scheme = arg[15:].strip().lower()
            if color_scheme not in ("default", "gambit", "distinctipy"):
                print(
                    "Warning: color-scheme must be default, gambit, or distinctipy; using default",
                    file=sys.stderr
                )
                color_scheme = "default"
        elif arg.endswith('.ef'):
            ef_file = arg
        else:
            # For backward compatibility, treat unknown args as filenames
            ef_file = arg
    
    # Determine output mode
    if png_requested:
        output_mode = "png"
    elif pdf_requested:
        output_mode = "pdf"
    elif tex_requested:
        output_mode = "tex"
    else:
        output_mode = "tikz"
    
    return (output_mode, pdf_requested, png_requested, tex_requested, output_file, dpi, color_scheme)

def ef_to_tex(
    ef_file: str,
    scale_factor: float = 1.0,
    show_grid: bool = False,
    color_scheme: str = "default",
    action_label_position: float = 0.5,
) -> str:
    """
    Convert an extensive form (.ef) file to TikZ code.

    This function replicates the main processing logic but returns the TikZ code
    as a string instead of printing it to stdout.

    Args:
        ef_file: Path to the .ef file to process.
        scale_factor: Scale factor for the diagram (default: 1.0).
        show_grid: Whether to show grid lines (default: False).
        color_scheme: Color scheme for player nodes.
        action_label_position: Position of action labels along edges.

    Returns:
        Complete TikZ code as a string.
    """
    # Scale adjustment
    scale_factor = scale_factor*0.8

    global scale, grid, node_to_iset_player

    # Save original state
    original_outstream = outstream.copy()
    original_stream0 = stream0.copy()
    original_nodes = nodes.copy()
    original_xshifts = xshifts.copy()
    original_playerdefined = playerdefined.copy()
    original_scale = scale
    original_grid = grid
    original_node_to_iset_player = node_to_iset_player.copy()

    try:
        # Reset global state
        outstream.clear()
        stream0.clear()
        nodes.clear()
        xshifts.clear()
        node_to_iset_player.clear()
        for i in range(len(playerdefined)):
            playerdefined[i] = False

        # Set parameters
        scale = scale_factor
        grid = show_grid

        # Process the .ef file
        lines = readfile(ef_file)

        # FIRST: Pre-parse all iset commands to build node-to-player mapping
        parse_isets_first(lines)

        # begin tikz picture
        outs("\\begin{tikzpicture}[scale=" + str(scale), stream0)
        ss = "  , StealthFill/.tip={Stealth[line width=.7pt"
        outs(ss + ",inset=0pt,length=13pt,angle'=30]}]", stream0)
        ss = ""
        if not grid:
            ss = "% "
        outs(ss + "\\draw [help lines, color=green] (-5,0) grid (5,-6);", stream0)

        # main loop - draw edges and information sets first
        for line in lines:
            comment(line)
            words = line.split()
            if len(words) > 0:
                if words[0] == "player":
                    player(words)
                elif words[0] == "level":
                    level(words, color_scheme, action_label_position)
                elif words[0] == "iset":
                    isetgen(words, color_scheme)

        # Draw all nodes on top of edges
        drawnodes(color_scheme)

        # Add legend if using non-default color scheme
        if color_scheme != "default":
            # Collect all unique players from the tree
            player_set = set()
            for nodeid in nodes:
                p = nodes[nodeid]["player"]
                if p >= 0:
                    player_set.add(p)

            legend_code = generate_legend(list(player_set), color_scheme, scale_factor)
            if legend_code:
                outs(legend_code, outstream)

        # end tikz picture - add to outstream so it comes after nodes
        outs("\\end{tikzpicture}", outstream)

        # Combine all output into a single string
        all_lines = stream0 + outstream
        return "\n".join(all_lines)

    finally:
        # Restore original state
        outstream.clear()
        outstream.extend(original_outstream)
        stream0.clear()
        stream0.extend(original_stream0)
        nodes.clear()
        nodes.update(original_nodes)
        xshifts.clear()
        xshifts.update(original_xshifts)
        node_to_iset_player.clear()
        node_to_iset_player.update(original_node_to_iset_player)
        for i in range(len(playerdefined)):
            playerdefined[i] = original_playerdefined[i]
        scale = original_scale
        grid = original_grid

def generate_tikz(
    game: str | "pygambit.gambit.Game",
    save_to: Optional[str] = None,
    scale_factor: float = 1.0,
    level_scaling: int = 1,
    sublevel_scaling: int = 1,
    width_scaling: int = 1,
    hide_action_labels: bool = False,
    shared_terminal_depth: bool = False,
    show_grid: bool = False,
    color_scheme: str = "default",
    edge_thickness: float = 1.0,
    action_label_position: float = 0.5,
) -> str:
    """
    Generate complete TikZ code from an extensive form (.ef) file.

    Args:
        game: Path to the .ef or .efg file to process, or a pygambit.gambit.Game object.
        save_to: Optional path to save intermediate .ef file when generating from a pygambit.gambit.Game object.
        scale_factor: Scale factor for the diagram.
        level_scaling: Level spacing multiplier used when generating from a pygambit.gambit.Game object.
        sublevel_scaling: Sublevel spacing multiplier used when generating from a pygambit.gambit.Game object.
        width_scaling: Width spacing multiplier used when generating from a pygambit.gambit.Game object.
        hide_action_labels: Whether to hide action labels when generating from a pygambit.gambit.Game object.
        shared_terminal_depth: Whether to enforce shared terminal depth when generating from a pygambit.gambit.Game object.
        show_grid: Whether to show grid lines.
        color_scheme: Color scheme for player nodes.
        edge_thickness: Thickness of edges.
        action_label_position: Position of action labels along edges.

    Returns:
        Complete TikZ code ready for use in Jupyter notebooks or LaTeX documents.
    """
    # If user supplied an EFG file, convert it to .ef first so the existing
    # ef-based pipeline can be reused. efg_dl_ef returns a path string when
    # it successfully writes the .ef file.
    ef_file = game
    if isinstance(game, str):
        if game.lower().endswith('.efg'):
            try:
                ef_file = efg_dl_ef(game)
            except Exception:
                # fall through and let ef_to_tex raise a clearer error later
                pass
    else:
        from .gambit_layout import gambit_layout_to_ef
        # Generate the ef, use normalised spacing options
        ef_file = gambit_layout_to_ef(
            game,
            save_to=save_to,
            level_multiplier=level_scaling*4,
            sublevel_multiplier=sublevel_scaling*2 ,
            xshift_multiplier=width_scaling*2,
            hide_action_labels=hide_action_labels,
            shared_terminal_depth=shared_terminal_depth,
        )

    # Step 1: Generate the tikzpicture content using ef_to_tex logic
    tikz_picture_content = ef_to_tex(ef_file, scale_factor, show_grid, color_scheme, action_label_position)
    
    # Step 2: Define built-in macro definitions (from macros-drawtree.tex)
    macro_definitions = [
        "\\newdimen\\ndiam",
        "\\ndiam1.5mm",
        "\\newdimen\\sqwidth",
        "\\sqwidth1.6mm",
        "\\newdimen\\spx",
        "\\spx.7mm",
        "\\newdimen\\spy",
        "\\spy.5mm",
        "\\newdimen\\yup",
        "\\yup0.5mm",
        "\\newdimen\\yfracup",
        "\\yfracup1mm",
        "\\newdimen\\paydown",
        "\\paydown2.5ex",
        "\\newdimen\\treethickn",
        f"\\treethickn{edge_thickness}pt",
    ]
    # Step 2a: Define player color macros
    distinctipy_n = None
    if color_scheme == "distinctipy" and isinstance(ef_file, str) and ef_file.lower().endswith(".ef"):
        try:
            max_player = get_max_player_index_from_ef(ef_file)
            distinctipy_n = min(max_player + 1, MAX_COLOR_SCHEME_PLAYERS)
        except Exception:
            pass
    macro_definitions.extend(color_definitions(color_scheme, n=distinctipy_n))

    # Step 3: Combine everything into complete TikZ code
    tikz_code = """% TikZ code with built-in styling for game trees
% TikZ libraries required for game trees
\\usetikzlibrary{shapes}
\\usetikzlibrary{arrows.meta}

% Style settings for game tree formatting
\\tikzset{
    every node/.append style={font=\\rmfamily},
    every text node part/.append style={align=center},
    node distance=1.5mm,
    thick
}

% Built-in macro definitions for game tree drawing
"""

    # Add macro definitions
    for macro in macro_definitions:
        tikz_code += macro + "\n"

    tikz_code += f"\n% Game tree content from {ef_file}\n"
    tikz_code += tikz_picture_content

    return tikz_code


def draw_tree(
    game: str | "pygambit.gambit.Game",
    save_to: Optional[str] = None,
    scale_factor: float = 1.0,
    level_scaling: int = 1,
    sublevel_scaling: int = 1,
    width_scaling: int = 1,
    hide_action_labels: bool = False,
    shared_terminal_depth: bool = False,
    show_grid: bool = False,
    color_scheme: str = "default",
    edge_thickness: float = 1.0,
    action_label_position: float = 0.5,
) -> Optional[str]:
    """
    Generate TikZ code and display in Jupyter notebooks.

    Args:
        game: Path to the .ef or .efg file to process, or a pygambit.gambit.Game object.
        save_to: Optional path to save intermediate .ef file when generating from a pygambit.gambit.Game object.
        scale_factor: Scale factor for the diagram.
        level_scaling: Level spacing multiplier used when generating from a pygambit.gambit.Game object.
        sublevel_scaling: Sublevel spacing multiplier used when generating from a pygambit.gambit.Game object.
        width_scaling: Width spacing multiplier used when generating from a pygambit.gambit.Game object.
        hide_action_labels: Whether to hide action labels when generating from a pygambit.gambit.Game object.
        shared_terminal_depth: Whether to enforce shared terminal depth when generating from a pygambit.gambit.Game object.
        show_grid: Whether to show grid lines.
        color_scheme: Color scheme for player nodes.
        edge_thickness: Thickness of edges.
        action_label_position: Position of action labels along edges.

    Returns:
        The result of the Jupyter cell magic execution, or the TikZ code string
        if cell magic fails.
    """

    # Generate TikZ code
    tikz_code = generate_tikz(
        game,
        save_to=save_to,
        scale_factor=scale_factor,
        level_scaling=level_scaling,
        sublevel_scaling=sublevel_scaling,
        width_scaling=width_scaling,
        show_grid=show_grid,
        shared_terminal_depth=shared_terminal_depth,
        hide_action_labels=hide_action_labels,
        color_scheme=color_scheme,
        edge_thickness=edge_thickness,
        action_label_position=action_label_position,
    )

    # Execute cell magic or return TikZ
    ip = get_ipython()
    if ip:
        em = getattr(ip, 'extension_manager', None)
        loaded = getattr(em, 'loaded', None)
        try:
            jpt_loaded = 'jupyter_tikz' in loaded  # type: ignore
        except Exception:
            jpt_loaded = False
        if not jpt_loaded:
            ip.run_line_magic("load_ext", "jupyter_tikz")
        return ip.run_cell_magic("tikz", "", tikz_code)
    else:
        return tikz_code


def latex_wrapper(tikz_code: str) -> str:
    """
    Wrap TikZ code in a complete LaTeX document.
    
    Args:
        tikz_code: The TikZ code to embed in the document.
    Returns:
        Complete LaTeX document as a string.
    """
    latex_document = f"""\\documentclass[tikz,border=10pt]{{standalone}}
                        \\usepackage{{newpxtext,newpxmath}}
                        \\linespread{{1.10}}
                        \\usetikzlibrary{{shapes}}
                        \\usetikzlibrary{{arrows.meta}}

                        \\begin{{document}}

                        {tikz_code}

                        \\end{{document}}
                        """
    return latex_document


def generate_tex(
    game: str | "pygambit.gambit.Game",
    save_to: Optional[str] = None,
    scale_factor: float = 1.0,
    level_scaling: int = 1,
    sublevel_scaling: int = 1,
    width_scaling: int = 1,
    hide_action_labels: bool = False,
    shared_terminal_depth: bool = False,
    show_grid: bool = False,
    color_scheme: str = "default",
    edge_thickness: float = 1.0,
    action_label_position: float = 0.5,
) -> str:
    """
    Generate a complete LaTeX document file directly from an extensive form (.ef) file.

    This function creates a complete LaTeX document with embedded TikZ code
    and saves it to a .tex file.

    Args:
        game: Path to the .ef or .efg file to process, or a pygambit.gambit.Game object.
        save_to: path to save intermediate .ef file when generating from a pygambit.gambit.Game object and output tex file.
        scale_factor: Scale factor for the diagram.
        level_scaling: Level spacing multiplier used when generating from a pygambit.gambit.Game object.
        sublevel_scaling: Sublevel spacing multiplier used when generating from a pygambit.gambit.Game object.
        width_scaling: Width spacing multiplier used when generating from a pygambit.gambit.Game object.
        hide_action_labels: Whether to hide action labels when generating from a pygambit.gambit.Game object.
        shared_terminal_depth: Whether to enforce shared terminal depth when generating from a pygambit.gambit.Game object.
        show_grid: Whether to show grid lines.
        color_scheme: Color scheme for player nodes.
        edge_thickness: Thickness of edges.
        action_label_position: Position of action labels along edges.

    Returns:
        Path to the generated LaTeX file.

    Raises:
        FileNotFoundError: If the .ef file doesn't exist.
    """
    # Determine output filename
    if save_to is None:
        if isinstance(game, str):
            game_path = Path(game)
        else:
            game_path = Path(game.title + '.ef')
        output_tex = game_path.with_suffix('.tex').name
    else:
        if not save_to.endswith('.tex'):
            output_tex = save_to + '.tex'
        else:
            output_tex = save_to
    
    # If game is an EFG file, convert it first
    if isinstance(game, str) and game.lower().endswith(".efg"):
        try:
            game = efg_dl_ef(game)
        except Exception:
            pass

    # Generate TikZ content using generate_tikz
    tikz_code = generate_tikz(
        game,
        save_to=save_to,
        scale_factor=scale_factor,
        level_scaling=level_scaling,
        sublevel_scaling=sublevel_scaling,
        width_scaling=width_scaling,
        show_grid=show_grid,
        shared_terminal_depth=shared_terminal_depth,
        hide_action_labels=hide_action_labels,
        color_scheme=color_scheme,
        edge_thickness=edge_thickness,
        action_label_position=action_label_position,
    )
    
    # Wrap in complete LaTeX document
    latex_document = latex_wrapper(tikz_code)
    
    # Write to file
    with open(output_tex, 'w') as f:
        f.write(latex_document)
    
    return str(Path(output_tex).absolute())


def generate_pdf(
        game: str | "pygambit.gambit.Game",
        save_to: Optional[str] = None,
        scale_factor: float = 1.0,
        level_scaling: int = 1,
        sublevel_scaling: int = 1,
        width_scaling: int = 1,
        hide_action_labels: bool = False,
        shared_terminal_depth: bool = False,
        show_grid: bool = False,
        color_scheme: str = "default",
        edge_thickness: float = 1.0,
        action_label_position: float = 0.5,
        ) -> str:
    """
    Generate a PDF directly from an extensive form (.ef) file.

    This function creates a complete LaTeX document, compiles it to PDF,
    and optionally cleans up temporary files.

    Args:
        game: Path to the .ef or .efg file to process, or a pygambit.gambit.Game object.
        save_to: path to save intermediate .ef file when generating from a pygambit.gambit.Game object and output pdf file.
        scale_factor: Scale factor for the diagram.
        level_scaling: Level spacing multiplier used when generating from a pygambit.gambit.Game object.
        sublevel_scaling: Sublevel spacing multiplier used when generating from a pygambit.gambit.Game object.
        width_scaling: Width spacing multiplier used when generating from a pygambit.gambit.Game object.
        hide_action_labels: Whether to hide action labels when generating from a pygambit.gambit.Game object.
        shared_terminal_depth: Whether to enforce shared terminal depth when generating from a pygambit.gambit.Game object.
        show_grid: Whether to show grid lines.
        color_scheme: Color scheme for player nodes.
        edge_thickness: Thickness of edges.
        action_label_position: Position of action labels along edges.

    Returns:
        Path to the generated PDF file.

    Raises:
        FileNotFoundError: If the .ef file doesn't exist.
        subprocess.CalledProcessError: If LaTeX compilation fails.
    """
    # Determine output filename
    if save_to is None:
        if isinstance(game, str):
            game_path = Path(game)
        else:
            game_path = Path(game.title + ".ef")
        output_pdf = game_path.with_suffix(".pdf").name
    else:
        if not save_to.endswith(".pdf"):
            output_pdf = save_to + ".pdf"
        else:
            output_pdf = save_to

    # If game is an EFG file, convert it first
    if isinstance(game, str) and game.lower().endswith(".efg"):
        try:
            game = efg_dl_ef(game)
        except Exception:
            pass
    
    # Generate TikZ content using generate_tikz
    tikz_code = generate_tikz(
        game,
        save_to=save_to,
        scale_factor=scale_factor,
        level_scaling=level_scaling,
        sublevel_scaling=sublevel_scaling,
        width_scaling=width_scaling,
        show_grid=show_grid,
        shared_terminal_depth=shared_terminal_depth,
        hide_action_labels=hide_action_labels,
        color_scheme=color_scheme,
        edge_thickness=edge_thickness,
        action_label_position=action_label_position,
    )
    
    # Create LaTeX wrapper document
    latex_document = latex_wrapper(tikz_code)
    
    # Use temporary directory for LaTeX compilation
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write LaTeX file
        tex_file = temp_path / "output.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_document)
        
        # Compile with pdflatex
        try:
            subprocess.run([
                'pdflatex', 
                '-interaction=nonstopmode',
                '-output-directory', str(temp_path),
                str(tex_file)
            ], capture_output=True, text=True, check=True)
            
            # Move the generated PDF to the desired location
            generated_pdf = temp_path / "output.pdf"
            final_pdf_path = Path(output_pdf)
            
            if generated_pdf.exists():
                # Copy to final destination
                import shutil
                shutil.copy2(generated_pdf, final_pdf_path)
                return str(final_pdf_path.absolute())
            else:
                raise RuntimeError("PDF was not generated successfully")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"LaTeX compilation failed:\n{e.stderr}"
            if "command not found" in e.stderr or "No such file" in str(e):
                error_msg += "\n\nMake sure pdflatex is installed and available in your PATH."
            raise RuntimeError(error_msg)
        except FileNotFoundError:
            raise RuntimeError("pdflatex not found. Please install a LaTeX distribution (e.g., TeX Live, MiKTeX).")


def generate_png(
    game: str | "pygambit.gambit.Game",
    save_to: Optional[str] = None,
    scale_factor: float = 1.0,
    level_scaling: int = 1,
    sublevel_scaling: int = 1,
    width_scaling: int = 1,
    hide_action_labels: bool = False,
    shared_terminal_depth: bool = False,
    show_grid: bool = False,
    color_scheme: str = "default",
    edge_thickness: float = 1.0,
    action_label_position: float = 0.5,
    dpi: int = 300,
) -> str:
    """
    Generate a PNG image directly from an extensive form (.ef) file.

    This function creates a PDF first, then converts it to PNG using external tools.
    Requires both pdflatex and either ImageMagick (convert) or Ghostscript (gs).

    Args:
        game: Path to the .ef or .efg file to process, or a pygambit.gambit.Game object.
        save_to: path to save intermediate .ef file when generating from a pygambit.gambit.Game object and output png file.
        scale_factor: Scale factor for the diagram.
        level_scaling: Level spacing multiplier used when generating from a pygambit.gambit.Game object.
        sublevel_scaling: Sublevel spacing multiplier used when generating from a pygambit.gambit.Game object.
        width_scaling: Width spacing multiplier used when generating from a pygambit.gambit.Game object.
        hide_action_labels: Whether to hide action labels when generating from a pygambit.gambit.Game object.
        shared_terminal_depth: Whether to enforce shared terminal depth when generating from a pygambit.gambit.Game object.
        show_grid: Whether to show grid lines.
        color_scheme: Color scheme for player nodes.
        edge_thickness: Thickness of edges.
        action_label_position: Position of action labels along edges.

    Returns:
        Path to the generated PNG file.

    Raises:
        FileNotFoundError: If the .ef file doesn't exist.
        RuntimeError: If PDF generation or PNG conversion fails.
    """
    # Determine output filename
    if save_to is None:
        if isinstance(game, str):
            game_path = Path(game)
        else:
            game_path = Path(game.title + ".ef")
        output_png = game_path.with_suffix(".png").name
    else:
        if not save_to.endswith(".png"):
            output_png = save_to + ".png"
        else:
            output_png = save_to

    # If game is an EFG file, convert it first
    if isinstance(game, str) and game.lower().endswith(".efg"):
        try:
            game = efg_dl_ef(game)
        except Exception:
            pass
    
    # Step 1: Generate PDF first
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf = Path(temp_dir) / "temp_output.pdf"
        
        try:
            # Generate PDF using existing function
            generate_pdf(
                game=game,
                save_to=save_to,
                scale_factor=scale_factor,
                level_scaling=level_scaling,
                sublevel_scaling=sublevel_scaling,
                width_scaling=width_scaling,
                hide_action_labels=hide_action_labels,
                shared_terminal_depth=shared_terminal_depth,
                show_grid=show_grid,
                color_scheme=color_scheme,
                edge_thickness=edge_thickness,
                action_label_position=action_label_position,
            )
            
            # Step 2: Convert PDF to PNG
            final_png_path = Path(output_png)
            
            # Try different conversion methods in order of preference
            conversion_success = False
            
            # Method 1: Try ImageMagick convert
            try:
                subprocess.run([
                    'convert',
                    '-density', str(dpi),
                    '-quality', '100',
                    str(temp_pdf),
                    str(final_png_path)
                ], capture_output=True, text=True, check=True)
                conversion_success = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # Method 2: Try Ghostscript if ImageMagick failed
            if not conversion_success:
                try:
                    subprocess.run([
                        'gs',
                        '-dNOPAUSE',
                        '-dBATCH',
                        '-sDEVICE=png16m',
                        f'-r{dpi}',
                        f'-sOutputFile={final_png_path}',
                        str(temp_pdf)
                    ], capture_output=True, text=True, check=True)
                    conversion_success = True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            
            # Method 3: Try pdftoppm + convert if available
            if not conversion_success:
                try:
                    temp_ppm = Path(temp_dir) / "temp_output"
                    # Convert PDF to PPM first
                    subprocess.run([
                        'pdftoppm',
                        '-r', str(dpi),
                        str(temp_pdf),
                        str(temp_ppm)
                    ], capture_output=True, text=True, check=True)
                    
                    # Find the generated PPM file (pdftoppm adds -1.ppm suffix)
                    ppm_file = Path(temp_dir) / f"{temp_ppm.name}-1.ppm"
                    if ppm_file.exists():
                        # Convert PPM to PNG
                        subprocess.run([
                            'convert',
                            str(ppm_file),
                            str(final_png_path)
                        ], capture_output=True, text=True, check=True)
                        conversion_success = True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            
            if not conversion_success:
                raise RuntimeError(
                    "PNG conversion failed. Please install one of the following:\n"
                    "  - ImageMagick (provides 'convert' command)\n"
                    "  - Ghostscript (provides 'gs' command)\n"
                    "  - Poppler utils (provides 'pdftoppm' command)\n\n"
                    "Installation examples:\n"
                    "  macOS: brew install imagemagick ghostscript poppler\n"
                    "  Ubuntu: sudo apt-get install imagemagick ghostscript poppler-utils\n"
                    "  Windows: Install ImageMagick or Ghostscript from their websites"
                )
            
            if final_png_path.exists():
                return str(final_png_path.absolute())
            else:
                raise RuntimeError("PNG was not generated successfully")
                
        except FileNotFoundError:
            # Re-raise file not found errors directly
            raise
        except RuntimeError:
            # Re-raise PDF generation errors
            raise
        except Exception as e:
            raise RuntimeError(f"PNG generation failed: {e}")


def efg_dl_ef(efg_file: str) -> str:
    """Convert a Gambit .efg file to the `.ef` format used by generate_tikz.

    The function implements a focused parser and deterministic layout
    heuristics via the DefaultLayout class for producing `.ef` directives
    from a conservative subset of EFG records (chance nodes `c`, player nodes
    `p`, and terminals `t`). It emits node level/position lines and
    information-set (`iset`) groupings.

    Args:
        efg_file: Path to the input .efg file.

    Returns:
        Path to the written `.ef` file as a string.
    """

    lines = readfile(efg_file)


    # Extract players from header if present.
    header = "\n".join(lines[:5])
    m_players = re.search(r"\{\s*([\s\S]*?)\s*\}", header)
    player_names = []
    if m_players:
        player_names = re.findall(r'"([^\"]+)"', m_players.group(1))

    # Parse EFG records into descriptor objects.
    descriptors = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('%') or line.startswith('#'):
            continue
        tokens = line.split()
        if not tokens:
            continue
        kind = tokens[0]
        # extract moves in braces
        brace = re.search(r"\{([^}]*)\}", line)
        moves = []
        probs = []
        payoffs = []
        player = None
        if kind == 'c' or kind == 'p':
            if brace:
                moves = re.findall(r'"([^"\\]*)"', brace.group(1))
                # also extract probabilities (numbers) in brace
                probs = re.findall(r'([0-9]+\/[0-9]+|[0-9]*\.?[0-9]+)', brace.group(1))
            # attempt to find player id for 'p' lines
            if kind == 'p':
                # find first integer token after type
                nums = [t for t in tokens[1:] if t.isdigit()]
                if len(nums) >= 1:
                    player = int(nums[0])
                # if there is a second numeric token treat as info-set id
                iset_id = None
                if len(nums) >= 2:
                    iset_id = int(nums[1])
            else:
                iset_id = None
        elif kind == 't':
            # terminal: extract payoffs (allow integers and decimals)
            if brace:
                # Match floats like 12.80, .80, -1.5 or integers like 3
                pay_tokens = re.findall(r'(-?\d*\.\d+|-?\d+)', brace.group(1))
                payoffs = []
                for tok in pay_tokens:
                    # If token contains a decimal point treat as float and
                    # format with two decimal places (keeps trailing zeros),
                    # otherwise treat as integer.
                    if '.' in tok:
                        try:
                            v = float(tok)
                            payoffs.append("{:.2f}".format(v))
                        except Exception:
                            # fallback: keep original token
                            payoffs.append(tok)
                    else:
                        try:
                            payoffs.append(str(int(tok)))
                        except Exception:
                            payoffs.append(tok)
        descriptors.append({
            'kind': kind,
            'player': player,
            'moves': moves,
            'probs': probs,
            'payoffs': payoffs,
            'iset_id': locals().get('iset_id', None),
            'raw': line,
        })

    # Filter descriptors to only the game records (c, p, t)
    descriptors = [d for d in descriptors if d['kind'] in ('c', 'p', 't')]

    # Layout/emission: delegate to DefaultLayout class for clarity/testability
    layout = DefaultLayout(descriptors, player_names)
    out_lines = layout.to_lines()

    try:
        efg_path = Path(efg_file)
        out_path = efg_path.with_suffix('.ef')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines) + '\n')
        return str(out_path)
    except Exception:
        return '\n'.join(out_lines)
