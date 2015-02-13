# generic knit script
# set the CODE_DIR and the SCRIPT

library(knitr)
TARGET_DIR <- Sys.getenv("TARGET_DIR")
ITER       <- Sys.getenv("ITER")        # The iteration of model outputs to read

CODE_DIR   <- Sys.getenv("CODE_DIR")
SCRIPT     <- Sys.getenv("SCRIPT")
knit2html(file.path(CODE_DIR,paste0(SCRIPT,".Rmd")), 
          options = c('toc', markdown::markdownHTMLOptions(TRUE)))
