library(knitr)
knit2html("CoreSummaries.Rmd", options = c('toc', markdown::markdownHTMLOptions(TRUE)))
# knit2html("Test.Rmd")