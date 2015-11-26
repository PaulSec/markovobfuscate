from obfuscation import *
import logging
import re

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Regular expression to split our training files on
    split_regex = r'\.'

    # File/book to read for training the Markov model (will be read into memory)
    training_file = "./lyrics.txt"

    # Obfuscating Markov engine
    m = MarkovKeyState()

    # Read the shared key into memory
    with open(training_file, "r") as f:
        text = f.read()

    # Split learning data into sentences, in this case, based on periods.
    map(m.learn_sentence, re.split(split_regex, text))

    # Begin automated tests ######

#    for i in xrange(20):
 #       # Run a random test
  #      rand_string = "".join([chr(random.randint(0, 255)) for k in xrange(1024)])
   #     if rand_string != m.deobfuscate_string(m.obfuscate_string(rand_string)):
    #        raise AlgorithmFailException()

    # Proved to cause an infinite failure prefix
    #m.create_byte("ruinating", 217)

    # End automated tests ######

    # Our data to obfuscate
    test_string = "dGhpcyBpcyBhIGNyYXp5IG1lc3NhZ2UK"
    print "Original string: {0}".format(test_string)

    # Obfuscate the data
    s = m.obfuscate_string(test_string)
    print "Obfuscated string: {0}".format(s)

    # Other Markov engine
    m2 = MarkovKeyState()

    # Split learning data into sentences, in this case, based on periods.
    map(m2.learn_sentence, re.split(split_regex, text))

    # Print out the deobfuscated string
    print "Deobfuscated string: {0}".format(m2.deobfuscate_string(s)[1:])
