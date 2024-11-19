from rich.highlighter import RegexHighlighter


class DicomKeyHighlighter(RegexHighlighter):
	"""
	Highlights DICOM keys and forward slashes when printing with Rich.

	Attributes
	----------
	base_style : str
	    The base style for highlighted elements.
	highlights : list of str
	    Regular expressions used for highlighting.

	Examples
	--------
	>>> from rich.console import Console
	>>> highlighter = DicomKeyHighlighter()
	>>> console = Console(
	        highlighter=highlighter,
	        theme=Theme(
	            {
	                "example.DicomTag": "bold magenta",
	            }
	        ),
	    )
	>>> console.print('%(PatientID)s/%(StudyID)s')

	Notes
	-----
	I dont know what is going on here, but it works lol
	"""

	base_style = 'example.'
	highlights = [
		r'%\((?P<DicomTag>[a-zA-Z0-9_]+)\)s',
		r'(?P<ForwardSlash>/)',
		r'(?P<Braces>\{[a-zA-Z0-9_]+\})',
	]
