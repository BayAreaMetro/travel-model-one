library(shiny)

controls <- function(person_num) {
  helpText( )

  inputPanel(
    helpText( h4(paste("Describe Person",person_num))),
    textInput(paste0("name",person_num), label=paste("Person",person_num,"Name")),
    sliderInput(paste0("age",person_num), "Age",
                min=0, max=100, value=40, step=1),

    selectInput(paste0("relate",person_num), "Relationship to householder",
                choices=c("Householder"                     = 1,
                          "Husband/wife"                    = 2,
                          "Natural born child"              = 3,
                          "Adopted child"                   = 4,
                          "Step child"                      = 5,
                          "Sibling"                         = 6,
                          "Parent"                          = 7,
                          "Grandchild"                      = 8,
                          "Parent-in-law"                   = 9,
                          "Son/Daughter-in-law"             = 10,
                          "Other relative"                  = 11,
                          "Brother/Sister-in-law"           = 12,
                          "Nephew/Niece"                    = 13,
                          "Grandparent"                     = 14,
                          "Uncle/Aunt"                      = 15,
                          "Cousin"                          = 16,
                          "Roomer/Boarder"                  = 17,
                          "Housemate/Roommate"              = 18,
                          "Unmarried partner"               = 19,
                          "Foster child"                    = 20,
                          "Other nonrelative"               = 21,
                          "Institutionalized GQ person"     = 22,
                          "Non-Institutionalized GQ person" = 23)),

    selectInput(paste0("esr",person_num), "Employment Status",
                choices=c("Under sixteen"                            = 0,
                          "Employed, at work"                        = 1,
                          "Employed, with a job but not at work"     = 2,
                          "Unemployed"                               = 3,
                          "Armed Forces, at work"                    = 4,
                          "Armed Forces, with a job but not at work" = 5,
                          "Not in labor force"                       = 6,
                          "Retired"                                  = 7), # this isn't an ESR option but added for ptype
                selected=1),

    selectInput(paste0("grade",person_num), "Grade of students or children under 3",
                choices=c("Not a student"                            = 0,
                          "Nursery school"                           = 1,
                          "Kindergarten"                             = 2,
                          "Grade 1 to 4"                             = 3,
                          "Grade 5 to 8"                             = 4,
                          "Grade 9 to 12"                            = 5,
                          "College undergraduate"                    = 6,
                          "Graduate or Professional School"          = 7)),

    radioButtons(paste0("sex",person_num),"Gender",
                 choices=c("Male"   = 1,
                           "Female" = 2)),
    # keep this?
    sliderInput(paste0("weeks",person_num), "Weeks worked in 1999",
                min=0, max=52, value=50, step=1),

    sliderInput(paste0("hours",person_num),"Hours worked per week in 1999",
                min=0, max=99, value=40, step=1),

    selectInput(paste0("msp",person_num), "Marital Status",
                choices=c("N/A" = 0,
                          "Now married, spouse present" = 1,
                          "Now married, spouse absent"  = 2,
                          "Widowed"                     = 3,
                          "Divorced"                    = 4,
                          "Separated"                   = 5,
                          "Never married"               = 6),
                selected=1),

    sliderInput(paste0("earns",person_num), "Personal Income (2015$)",
                min=0, max=470000, value=60000, step=5000, sep=",", pre="$")
  )
}

# Define UI for application that draws a histogram
shinyUI(fluidPage(

  # Application title
  titlePanel("Travel Model One: Thousand Mes!"),

  fluidRow(
    column(12,
      tags$style(type="text/css", "#error { color:red }"),
      conditionalPanel(condition="output.error",
                       verbatimTextOutput("error")),
      conditionalPanel(condition="output.status",
                       verbatimTextOutput("status"))
    )
  ),

  fluidRow(
    column(6,
      strong(style="font-size: 18px","Model Parameters"),
      wellPanel(
        verticalLayout( # how do i make this full width of the columns?
          textInput("pivot_dir",label="Pivot Directory", width="100%", value="D:/Projects/2010_05_003"),
          uiOutput("model_dir"),
          fluidRow(
            column(6,
              selectInput("me_count", "Number of mes",
                          choices=c("10"  = 10,
                                    "100" = 100,
                                    "500" = 500,
                                    "1000" = 1000),
                          selected=1000)),
            column(6,
                   helpText("This will be slow to proceed only after household and persons are set"),
                   actionButton("go_button", "Create Model Files!"))
          )
        )
      ),

      strong(style="font-size: 18px","Describe your Household"),
      span(a("(ref)", target="_blank", href="http://analytics.mtc.ca.gov/foswiki/Main/PopSynHousehold"), style="float:right"),
      wellPanel(
        fluidRow(
          column(6,
            span(a("(TAZ ref)", target="_blank", href="http://analytics.mtc.ca.gov/foswiki/Main/TravelModelOneGeographies"), style="float:right"),
            textInput("taz", label="Location (TAZ) of Household"),
             sliderInput("persons", "Number of Persons", min=1, max=12, value=2, step=1)
          ),
          column(6,
            selectInput("unittype", "Housing Unit Type",
                        choices=c("Housing unit"                     = 1,
                                  "Institutional group quarters"     = 2,
                                  "Non-institutional group quarters" = 3)),
             sliderInput("noc", "Number of own children under 18 years in household",
                         min=0, max=12, value=1, step=1)
          )
        ),
        selectInput("hht", "Household/Family Type",
                    choices=c("Family household: married couple"                           = 1,
                              "Family household: male householder, no wife present"        = 2,
                              "Family household: female householder, no husband present"   = 3,
                              "Non-family household: male householder, living alone"       = 4,
                              "Non-family household: male householder, not living alone"   = 5,
                              "Non-family household: female householder, living alone"     = 6,
                              "Non-family household: female householder, not living alone" = 7),
                    width='100%'),

        selectInput("bldgsz", "Building Size",
                    choices=c("Mobile home"                                     = 1,
                              "One-family house detached from any other house"  = 2,
                              "One family house attached to one or more houses" = 3,
                              "A building with 2 apartments"                    = 4,
                              "A building with 3 or 4 apartments"               = 5,
                              "A building with 5 to 9 apartments"               = 6,
                              "A building with 10 to 19 apartments"             = 7,
                              "A building with 20 to 49 apartments"             = 8,
                              "A building with 50 or more apartments"           = 9,
                              "A boat, RV, Van, etc."                           = 10),
                    selected=5),
        selectInput("tenure", "Home Ownership",
                    choices=c("Owned by you or someone in this household with a mortgage or a loan" = 1,
                              "Owned by you or someone in this household free and clear"            = 2,
                              "Rented for cash rent"                                                = 3,
                              "Occupied without payment of cash rent"                               = 4))
      )
    ),
    column(6,
      strong(style="font-size: 18px","Describe each person in your household"),
      span(a("(ref)", target="_blank", href="http://analytics.mtc.ca.gov/foswiki/Main/PopSynPerson"), style="float:right"),
      controls(1),
      conditionalPanel("input.persons >=2", controls(2)),
      conditionalPanel("input.persons >=3", controls(3)),
      conditionalPanel("input.persons >=4", controls(4)),
      conditionalPanel("input.persons >=5", controls(5)),
      conditionalPanel("input.persons >=6", controls(6)),
      conditionalPanel("input.persons >=7", controls(7)),
      conditionalPanel("input.persons >=8", controls(8)),
      conditionalPanel("input.persons >=9", controls(9)),
      conditionalPanel("input.persons >=10", controls(10)),
      conditionalPanel("input.persons >=11", controls(11)),
      conditionalPanel("input.persons >=12", controls(12))
    )
  ),


  fluidRow(
    helpText("Names"),
    tableOutput("name_table"),
    helpText("Household Table"),
    tableOutput('household_table'),
    helpText("Person Table"),
    tableOutput('person_table')
  )
))