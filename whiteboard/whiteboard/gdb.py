from subprocess import Popen, PIPE, DEVNULL

def parseAsyncOutput(text):
	record = {}
	commaPos = text.find(',')
	if commaPos == -1:
		record['class'] = text
	else:
		record['class'] = text[:commaPos]
		result, _ = parseResult(text[commaPos+1:])
		record['result'] = result
	
	return record

def parseResult(text):
	eqPos = text.find('=')
	key = text[:eqPos]
	value, l = parseValue(text[eqPos+1:])
	return { key : value }, eqPos+l+1

def parseValue(text):
	#print('parseValue: %s" % text)
	if text[0] == '"':
		return parseString(text)
	elif text[0] == "[":
		return parseList(text)
	elif text[0] == "{":
		return parseTuple(text)
	else:
		raise ValueError("unable to parse value: %s" % text)

def parseValueOrResult(text):
	#print('parseValue: %s" % text)
	if text[0] == '"':
		return parseString(text)
	elif text[0] == "[":
		return parseList(text)
	elif text[0] == "{":
		return parseTuple(text)
	else:
		return parseResult(text)

def parseString(text):
	if text[0] != '"':
		raise ValueError("Error parsing string")

	value = ''
	pos = 1
	while text[pos] != '"':
		if text[pos] == '\\':
			pos = pos + 1
			value = value + text[pos]
		else:
			value = value + text[pos]
		pos = pos + 1

	return text[1:pos], pos+1
	
def parseList(text):
	assert text[0] == '['
	pos = 1
	result = []
	while text[pos] != ']':
		r, l = parseValueOrResult(text[pos:])
		result.append(r)
		pos = pos + l
		if text[pos] == ',':
			pos = pos+1
		elif text[pos] != ']':
			raise ValueError("Error parsing list %s" % text[pos:])
	
	return result, pos+1
		
	
def parseTuple(text):
	assert text[0] == '{'
	result = {}
	pos = 1
	while text[pos] != '}':
		r, l = parseResult(text[pos:])
		result.update(r)
		pos = pos + l
		if text[pos] == ',':
			pos = pos+1
		elif text[pos] != '}':
			raise ValueError("Error parsing tuple %s" % text[pos:])
	
	return result, pos+1
		


class Gdb:
	"""GDB Session"""

	def __init__(self, binary):
		"""Creates GDB session on binary"""

		print("Created GDB session")

		args=['gdb', '--interpreter=mi', binary]
		self.process = Popen(args, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, universal_newlines=True)

		self.read()
		self.command('tty /dev/null') # TODO: redircet to a pipe, capture

	def read(self):
		""" Read all input from the debugger, untile the "(gdb)" marker """
		result = []
		for line in self.process.stdout:
			stripped = line.strip() # TODO must a clever, pythonish way to do it in the for statemen
			
			if stripped == '(gdb)':
				break
			r = self.processLine(stripped)
			if r is not None:
				result.append(r)
		return result

	def send(self, command):
		""" Sends command to GDB, returns result """
		self.process.stdin.write(command+"\n")
		self.process.stdin.flush()
		return self.read()
		
	def command(self, command):
		""" Sends command, retruns (result-record, oob-records) """
		result = None
		oobs = []
		
		records = self.send(command)
		for r in records:
			if r['type'] == '^':
				result = r
			else:
				oobs.append(r)
		
		assert result
		if result['class'] == 'error':
			raise RuntimeError("Error executing gdb command %s : %s" % (command, result['result']))
		
		return result, oobs
		
	def processLine(self, line):
		type = line[0]
		text = line[1:]

		if type not in ['~', '@', '&']:
			#print('line %s' % line)
			record = parseAsyncOutput(text)
			record.update({'type':type})
			#print('record: %s' % record)
			return record

