from obfuscation import *
import logging
import re

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Obfuscating Markov engine
    m = MarkovKeyState("./lyrics.txt")

    # Our data to obfuscate
    test_string = "dGhpcyBpcyBhIGNyYXp5IG1lc3NhZ2UK"
    print "Original string: {0}".format(test_string)

    # Obfuscate the data
    s = m.obfuscate_string(test_string)
    print "Obfuscated string: {0}".format(s)

    # Other Markov engine
    m2 = MarkovKeyState("./lyrics.txt")

    # Print out the deobfuscated string
    print "Deobfuscated string: {0}".format(m2.deobfuscate_string(s)[1:])
