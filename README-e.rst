##########################
panda_assignment_mksummary
##########################

For PandA, the materials submitted by assignment tool are distributed in separated folders for each user.
However, this structure is not suitable for teacher to preview all materials quickly.

mksummary.py (mksummary.exe) flattens the contents of submitted materials in one HTML file, including;

* Student name and id
* submission timestamp
* contents of html text
* attached files; if the attachment is image, embed it, shown as link to entire file.


Usage (for Windows)
========================

1. Download the latest mksummary.exe from https://github.com/takaakiaoki/panda_assignment_summary/releases ,
   and put this mksummary.exe file on your desktop.

2. The submitted materials are packed as in following list. You select one of those

   * folder of 'assignment_title'
   * any **file** within 'assignment_title' foler, such as 'grades.csv'

   and drag and drop onto the icon of mksummary.exe. A file 'summary.html' will be generated in the 'assignment_title' folder.

   ::

      bulk_download.zip
        - assignment_title/  <-- D & D this folder
          - grades.csv       <-- or this file
          - student_name, (student_id)/
            - student_name, (student_id)_submission_text.html
            - timestamp.txt
            - attachments/
              - file1
              - file2
              :
          - student_name, (student_id)/
          - student_name, (student_id)/
          - student_name, (student_id)/
          :
          - summary.html <-- this file is generated

3. Open summary.html in your browser and preview the submitted materials.
   
   Additionally, you may score the submission for each student in 'score' form. The personal scores can be summarized in one sheet, when 'show score sheet' button on the top of the html page.
   The contents of score sheet may be copied to grades.csv or grades.xlsx and uploaded to PandA.


For other OSs
========================

For Mac, Unix (and Windows), python should be installed to run mksummary.py 

::

   at 'assignment_title' folder,

   > mksummary.py

or, path to assignment folder should be given for the 1st argument of mksummary.py

::

   > mksummary.py <path_to_assignment_folder>


* mksummary.py is tested on python version 3.4 or 3.5
* mksummary.py requires following additional module, which is available on PyPI

  - pytz  (pip install pytz)


Acknowledgement
===============

The author appreciates to Prof. Hajime KITA, Kyoto University, for his inspiring prototype and kind advise.
