#!/usr/bin/env python

import ROOT
import re
import pprint
import sys
import inspect
import optparse
from Validation.Tools.GenObject import GenObject

defsDict = {
    'int'    : '%-40s : form=%%%%8d     type=int',
    'float'  : '%-40s : form=%%%%7.2f   prec=1e-5',
    'str'    : '%-40s : form=%%%%20s    type=string',
    'long'   : '%-40s : form=%%%%10d    type=long',    
    }

root2GOtypeDict = {
    'int'                      : 'int',
    'float'                    : 'float',
    'double'                   : 'float',
    'long'                     : 'long',
    'long int'                 : 'long',
    'unsigned int'             : 'int',
    'bool'                     : 'int',
    'string'                   : 'str',
    'std::basic_string<char>'  : 'str',
    }

startString = """
# -*- sh -*- For Font lock mode

###########################
## GenObject Definitions ##
###########################

# GenObject 'event' definition
[runevent singleton]
run:   type=int
event: type=int
"""

defTemplate = """
#####################
## %(OBJS)s Definition ##
#####################

# Nickname and Tree
[%(objs)s:FWLite]

# 'reco'-tupe 'runevent' 'tofill' information
[runevent:%(objs)s:EventAuxiliary shortcut=eventAuxiliary()]
run:   run()
event: event()

"""

colonRE     = re.compile (r':')
dotRE       = re.compile (r'\.')
nonAlphaRE  = re.compile (r'\W')
alphaRE     = re.compile (r'(\w+)')
vetoedTypes = set()


def getObjectList (objectName, base):
    """Get a list of interesting things from this object"""
    # The autoloader needs an object before it loads its dictionary.
    # So let's give it one.
    rootObjConstructor = getattr (ROOT, objectName)
    obj = rootObjConstructor()
    alreadySeenFunction = set()
    etaFound, phiFound = False, False
    global vetoedTypes
    retval = []
    # Put the current class on the queue and start the while loop
    reflexList = [ ROOT.Reflex.Type.ByName (objectName) ]
    while reflexList:
        reflex = reflexList.pop (0) # get first element
        print "Looking at %s" % reflex.Name (0xffffffff)
        for baseIndex in range( reflex.BaseSize() ) :
            reflexList.append( reflex.BaseAt(baseIndex).ToType() )
        for index in range( reflex.FunctionMemberSize() ):
            funcMember = reflex.FunctionMemberAt (index)
            # if we've already seen this, don't bother again
            name = funcMember.Name()
            if name == 'eta':
                etaFound = True
            elif name == 'phi':
                phiFound = True
            if name in alreadySeenFunction:
                continue
            # make sure this is an allowed return type
            returnType = funcMember.TypeOf().ReturnType().Name (0xffffffff)
            goType     = root2GOtypeDict.get (returnType, None)
            if not goType:
                vetoedTypes.add (returnType)
                continue
            # only bother printout out lines where it is a const function
            # and has no input parameters.            
            if funcMember.IsConst() and not funcMember.FunctionParameterSize():
                retval.append( ("%s.%s()" % (base, name), goType))
                alreadySeenFunction.add( name )
    retval.sort()
    return retval, etaFound and phiFound


def genObjNameDef (line):
    """Returns GenObject name and ntuple definition function"""
    words = dotRE.split (line)[1:]
    func = ".".join (words)
    name =  "_".join (words)
    name = nonAlphaRE.sub ('', name)
    return name, func
    
    
def genObjectDef (mylist, tuple, alias, label, type, etaPhiFound):
    """ """
    print "tuple %s alias %s label %s type %s" % (tuple, alias, label, type)
    # first get the name of the object
    firstName = mylist[0][0]
    match = alphaRE.match (firstName)
    if not match:
        raise RuntimeError, "firstName doesn't parse correctly. (%s)" \
              % firstName
    genName = match.group (1)
    genDef =  " ## GenObject %s Definition ##\n[%s]\n" % \
             (genName, genName)
    if options.index or not etaPhiFound:
        # either we told it to always use index OR either eta or phi
        # is missing.
        genDef += "-equiv: index,0\n";
    else:
        genDef += "-equiv: eta,0.1 phi,0.1\n";
    tupleDef = '[%s:%s:%s label=%s type=%s]\n' % \
               (genName, tuple, alias, label, type)
    
    for variable in mylist:
        name, func = genObjNameDef (variable[0])
        typeInfo   = variable[1]
        form = defsDict[ typeInfo ]
        genDef   += form % name + '\n'
        tupleDef += "%-40s : %s\n" % (name, func)
    return genDef, tupleDef


if __name__ == "__main__":
    # Setup options parser
    parser = optparse.OptionParser \
             ("usage: %prog [options]  objectName\n" \
              "Creates control file for GenObject.")
    parser.add_option ('--output', dest='output', type='string',
                       default = '',
                       help="Output (Default 'objectName.txt')")
    parser.add_option ('--alias', dest='alias', type='string',
                       default = 'dummyAlias',
                       help="Tell GO to set an alias")
    parser.add_option ('--label', dest='label', type='string',
                       default = 'dummyLabel',
                       help="Tell GO to set an label")
    parser.add_option ('--type', dest='type', type='string',
                       default = 'dummyType',
                       help="Tell GO to set an type")
    parser.add_option ('--goName', dest='goName', type='string',
                       default='',
                       help='GenObject name')
    parser.add_option ('--index', dest='index', action='store_true',
                       help='use index for matching')
    parser.add_option ('--tupleName', dest='tupleName', type='string',
                       default = 'reco',
                       help="Tuple name (default '%default')")
    options, args = parser.parse_args()
    options.type = GenObject.decodeNonAlphanumerics (options.type)
    if len (args) < 1:
        raise RuntimeError, "Need to provide object name."
    #
    objectName = args[0]    
    goName     = options.goName or colonRE.sub ('', objectName)
    outputFile = options.output or goName + '.txt'
    ROOT.gROOT.SetBatch()
    # load the right libraries, etc.
    ROOT.gSystem.Load("libFWCoreFWLite")
    ROOT.gSystem.Load("libDataFormatsFWLite")   
    ROOT.gSystem.Load("libReflexDict")
    ROOT.AutoLibraryLoader.enable()
    mylist, etaPhiFound = getObjectList (objectName, goName)
    targetFile = open (outputFile, 'w')
    genDef, tupleDef = genObjectDef (mylist,
                                     options.tupleName,
                                     goName,
                                     options.label,
                                     options.type,
                                     etaPhiFound)
    targetFile.write (startString)
    targetFile.write (genDef)
    targetFile.write (defTemplate % {'objs':'reco', 'OBJS':'RECO'})
    targetFile.write (tupleDef)
    print "Vetoed types:"
    pprint.pprint ( sorted( list(vetoedTypes) ) )
