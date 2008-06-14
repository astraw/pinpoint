# The default rule is to build the documentation.
default: docs

# Search the current directory for *.txt, replace '.txt' with '.html'.
HTML_products := $(patsubst %.txt,%.html,$(wildcard *.txt))

clean:
	rm -f $(HTML_products)

docs: $(HTML_products)

# This rule describes how to build .html files from .txt files.
%.html : %.txt
	rst2html $< $@

.PHONY: docs default clean
