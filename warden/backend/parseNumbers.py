# coding: utf-8
# Source: https://github.com/hayj/SystemTools/blob/master/systemtools/number.py
import re


def parseNumber(text):
    """
        Return the first number in the given text for any locale.
        TODO we actually don't take into account spaces for only
        3-digited numbers (like "1 000") so, for now, "1 0" is 10.
        TODO parse cases like "125,000.1,0.2" (125000.1).

        :example:
        >>> parseNumber("a 125,00 €")
        125
        >>> parseNumber("100.000,000")
        100000
        >>> parseNumber("100 000,000")
        100000
        >>> parseNumber("100,000,000")
        100000000
        >>> parseNumber("100 000 000")
        100000000
        >>> parseNumber("100.001 001")
        100.001
        >>> parseNumber("$.3")
        0.3
        >>> parseNumber(".003")
        0.003
        >>> parseNumber(".003 55")
        0.003
        >>> parseNumber("3 005")
        3005
        >>> parseNumber("1.190,00 €")
        1190
        >>> parseNumber("1190,00 €")
        1190
        >>> parseNumber("1,190.00 €")
        1190
        >>> parseNumber("$1190.00")
        1190
        >>> parseNumber("$1 190.99")
        1190.99
        >>> parseNumber("$-1 190.99")
        -1190.99
        >>> parseNumber("1 000 000.3")
        1000000.3
        >>> parseNumber('-151.744122')
        -151.744122
        >>> parseNumber('-1')
        -1
        >>> parseNumber("1 0002,1.2")
        10002.1
        >>> parseNumber("")

        >>> parseNumber(None)

        >>> parseNumber(1)
        1
        >>> parseNumber(1.1)
        1.1
        >>> parseNumber("rrr1,.2o")
        1
        >>> parseNumber("rrr1rrr")
        1
        >>> parseNumber("rrr ,.o")

    """
    try:
        # First we return None if we don't have something in the text:
        if text is None:
            return None
        if isinstance(text, int) or isinstance(text, float):
            return text
        text = text.strip()
        if text == "":
            return None
        # Next we get the first "[0-9,. ]+":
        n = re.search("-?[0-9]*([,. ]?[0-9]+)+", text).group(0)
        n = n.strip()
        if not re.match(".*[0-9]+.*", text):
            return None
        # Then we cut to keep only 2 symbols:
        while " " in n and "," in n and "." in n:
            index = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            n = n[0:index]
        n = n.strip()
        # We count the number of symbols:
        symbolsCount = 0
        for current in [" ", ",", "."]:
            if current in n:
                symbolsCount += 1
        # If we don't have any symbol, we do nothing:
        if symbolsCount == 0:
            pass
        # With one symbol:
        elif symbolsCount == 1:
            # If this is a space, we just remove all:
            if " " in n:
                n = n.replace(" ", "")
            # Else we set it as a "." if one occurence, or remove it:
            else:
                theSymbol = "," if "," in n else "."
                if n.count(theSymbol) > 1:
                    n = n.replace(theSymbol, "")
                else:
                    n = n.replace(theSymbol, ".")
        else:
            # Now replace symbols so the right symbol is "." and all left are "":
            rightSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            rightSymbol = n[rightSymbolIndex:rightSymbolIndex + 1]
            if rightSymbol == " ":
                return parseNumber(n.replace(" ", "_"))
            n = n.replace(rightSymbol, "R")
            leftSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            leftSymbol = n[leftSymbolIndex:leftSymbolIndex + 1]
            n = n.replace(leftSymbol, "L")
            n = n.replace("L", "")
            n = n.replace("R", ".")
        # And we cast the text to float or int:
        n = float(n)
        if n.is_integer():
            return int(n)
        else:
            return n
    except Exception:
        pass
    return None


def truncateFloat(f, n=2):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return float('{0:.{1}f}'.format(f, n))
    i, p, d = s.partition('.')
    return float('.'.join([i, (d+'0'*n)[:n]]))


def removeCommasBetweenDigits(text):
    """
        :example:
        >>> removeCommasBetweenDigits("sfeyv dsf,54dsf ef 6, 6 zdgy 6,919 Photos and 3,3 videos6,")
        'sfeyv dsf,54dsf ef 6, 6 zdgy 6919 Photos and 33 videos6,'
    """
    if text is None:
        return None
    else:
        return re.sub(r"([0-9]),([0-9])", "\g<1>\g<2>", text)


def getAllNumbers(text, removeCommas=False):
    if text is None:
        return None
    if removeCommas:
        text = removeCommasBetweenDigits(text)
    allNumbers = []
    if len(text) > 0:
        # Remove space between digits :
        spaceNumberExists = True
        while spaceNumberExists:
            text = re.sub('(([^.,0-9]|^)[0-9]+) ([0-9])', '\\1\\3', text, flags=re.UNICODE)
            if re.search('([^.,0-9]|^)[0-9]+ [0-9]', text) is None:
                spaceNumberExists = False
        numberRegex = '[-+]?[0-9]+[.,][0-9]+|[0-9]+'
        allMatchIter = re.finditer(numberRegex, text)
        if allMatchIter is not None:
            for current in allMatchIter:
                currentFloat = current.group()
                currentFloat = re.sub("\s", "", currentFloat)
                currentFloat = re.sub(",", ".", currentFloat)
                currentFloat = float(currentFloat)
                if currentFloat.is_integer():
                    allNumbers.append(int(currentFloat))
                else:
                    allNumbers.append(currentFloat)
    return allNumbers


def removeAllNumbers(text):
    if text is None:
        return None
    if len(text) == 0:
        return ""
    # Remove space between digits :
    spaceNumberExists = True
    while spaceNumberExists:
        text = re.sub('([0-9]) ([0-9])', '\\1\\2', text, flags=re.UNICODE)
        if re.search('[0-9] [0-9]', text) is None:
            spaceNumberExists = False
    numberRegex = '[-+]?[0-9]+[.,][0-9]+|[0-9]+'
    numberExists = True
    while numberExists:
        text = re.sub(numberRegex, "", text)
        if re.search(numberRegex, text) is None:
            numberExists = False

    return text.strip()


def getFirstNumber(text, *args, **kwargs):
    result = getAllNumbers(text, *args, **kwargs)
    if result is not None and len(result) > 0:
        return result[0]
    return None


def representsFloat(text):
    """
        This function return True if the given param (string or float) represents a float

        :Example:
        >>> representsFloat("1.0")
        True
        >>> representsFloat("1")
        False
        >>> representsFloat("a")
        False
        >>> representsFloat(".0")
        False
        >>> representsFloat("0.")
        False
        >>> representsFloat("0.000001")
        True
        >>> representsFloat("00000.000001")
        True
        >>> representsFloat("0000a0.000001")
        False
    """
    if isinstance(text, float):
        return True
    elif text is None:
        return False
    elif isinstance(text, str):
        if len(text) < 3:
            return False
        text = text.strip()
        return re.search("^[0-9]{1,}\.[0-9]{1,}$", text) is not None
    else:
        return False


def representsInt(s, acceptRoundedFloats=False):
    """
        This function return True if the given param (string or float) represents a int

        :Example:
        >>> representsInt(1)
        True
        >>> representsInt("1")
        True
        >>> representsInt("a")
        False
        >>> representsInt("1.1")
        False
        >>> representsInt(1.1)
        False
        >>> representsInt(42.0, acceptRoundedFloats=True)
        True
        >>> representsInt("42.0", acceptRoundedFloats=True)
        True
    """

    if isinstance(s, float):
        if acceptRoundedFloats:
            return s.is_integer()
    else:
        if acceptRoundedFloats:
            try:
                s = float(s)
                return representsInt(s, acceptRoundedFloats=acceptRoundedFloats)
            except ValueError:
                return False
        else:
            try:
                int(s)
                return True
            except ValueError:
                return False
    return False


def floatAsReadable(f):
    """
        source https://stackoverflow.com/questions/8345795/force-python-to-not-output-a-float-in-standard-form-scientific-notation-expo
    """
    _ftod_r = re.compile(br'^(-?)([0-9]*)(?:\.([0-9]*))?(?:[eE]([+-][0-9]+))?$')
    """Print a floating-point number in the format expected by PDF:
    as short as possible, no exponential notation."""
    s = bytes(str(f), 'ascii')
    m = _ftod_r.match(s)
    if not m:
        raise RuntimeError("unexpected floating point number format: {!a}"
                           .format(s))
    sign = m.group(1)
    intpart = m.group(2)
    fractpart = m.group(3)
    exponent = m.group(4)
    if ((intpart is None or intpart == b'') and
            (fractpart is None or fractpart == b'')):
        raise RuntimeError("unexpected floating point number format: {!a}"
                           .format(s))

    # strip leading and trailing zeros
    if intpart is None:
        intpart = b''
    else:
        intpart = intpart.lstrip(b'0')
    if fractpart is None:
        fractpart = b''
    else:
        fractpart = fractpart.rstrip(b'0')

    result = None

    if intpart == b'' and fractpart == b'':
        # zero or negative zero; negative zero is not useful in PDF
        # we can ignore the exponent in this case
        result = b'0'

    # convert exponent to a decimal point shift
    elif exponent is not None:
        exponent = int(exponent)
        exponent += len(intpart)
        digits = intpart + fractpart
        if exponent <= 0:
            result = sign + b'.' + b'0'*(-exponent) + digits
        elif exponent >= len(digits):
            result = sign + digits + b'0'*(exponent - len(digits))
        else:
            result = sign + digits[:exponent] + b'.' + digits[exponent:]

    # no exponent, just reassemble the number
    elif fractpart == b'':
        result = sign + intpart  # no need for trailing dot
    else:
        result = sign + intpart + b'.' + fractpart

    result = result.decode("utf-8")
    if result.startswith("."):
        result = "0" + result
    return result


def digitalizeIntegers(text, totalDigits=100):
    if text is None or not isinstance(text, str) or text == "":
        return text
    result = str(text)
    toEdit = []
    for current in re.finditer("[0-9]+", text):
        theInt = current.group(0)
        start = current.start(0)
        end = current.end(0)
        remainingDigits = totalDigits - len(theInt)
        digitalizedInt = "0" * remainingDigits + theInt
        toEdit.append((digitalizedInt, start, end))
    for digitalizedInt, start, end in reversed(toEdit):
        # print(digitalizedInt, start, end)
        result = result[:start] + digitalizedInt + result[end:]
    return result


def main():
    allTexts = \
        [
            "ttt1ttt3t",
            "zzz23.32zzz8",
            "3.0z",
            "aaaaa",
            "bb",
            None,
            "1111111111111111111111111111111111111111111",
            "5",
            "0",
        ]
    for current in allTexts:
        print(current)
        print(digitalizeIntegers(current))
        print()


if __name__ == '__main__':
    # print(list(range(1, -1, -1)))
    main()
