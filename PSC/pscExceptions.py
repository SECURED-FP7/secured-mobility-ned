#   
#   File:       pscExceptions.py
#   @author:    BSC
#   Description:
#       Custom execption class to manage error in the PSC
# 

class pscExceptions():

	class pscWrongProfileType(Exception):
		pass

	class TVDnotInstantiated(Exception):
		pass

	class PSAconfNotFound(Exception):
		pass
