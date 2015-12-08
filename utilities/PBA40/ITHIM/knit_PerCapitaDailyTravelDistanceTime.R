library(knitr)
CODE_DIR   <- Sys.getenv("CODE_DIR")
knit2html(file.path(CODE_DIR,"utilities","PBA40","ITHIM","PerCapitaDailyTravelDistanceTime.Rmd"), options = c('toc', markdown::markdownHTMLOptions(TRUE)))
# knit2html("Test.Rmd")