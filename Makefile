default: docs

clean:
	rm GOALS.html

docs: GOALS.html

GOALS.html: GOALS.txt
	rst2html GOALS.txt GOALS.html

.PHONY: docs default clean
