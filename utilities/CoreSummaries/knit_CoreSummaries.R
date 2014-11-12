library(knitr)
CODE_DIR   <- Sys.getenv("CODE_DIR")
knit2html(file.path(CODE_DIR,"CoreSummaries.Rmd"), options = c('toc', markdown::markdownHTMLOptions(TRUE)))
# knit2html("Test.Rmd")