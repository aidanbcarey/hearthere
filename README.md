Welcome to Hear, There and Everywhere! 

Getting started:

The website is designed to be run on Heroku. It takes advantage of Heroku Postgres for database management and RQ for job management. Fortunately, the website should be up-and-running in perpetuity so you can just access it at its URL, hearthere.herokuapp.com. The zipped file contains the folder I have pushed to Heroku, so it should contain everything necessary to run. When loading the website, it will probably take a minute or two for Heroku to reboot the site, so just be a little patient. 

APIs:

I use both the Spotify API and Genius API. The Genius API is very simple and just requires a single client secret that is hardcoded into application.py (bad practice but w/e). The Spotify API requires a redirect uri that is specified in the code (and must also be given to Spotify beforehand), which is a consideration to be made if one wants to run an instance website themselves instead of just using what I have uploaded.

Usage:
The functional purpose of the website is to allow people to compare the frequency of words in songs they listen to to the frequency of words in a reference database of lyrics (Top Spotify songs from 2010-2019 on Kaggle: https://www.kaggle.com/leonardopena/top-spotify-songs-from-20102019-by-year). 

The initial usage of the program is very similar to CS50: Finance. The login and registration features are identical except for some backend changes to the SQL client. 

Once logged in, you must authenticate with your Spotify account by clicking the button in front of you. Then log in using your credentials and the website is given a one time use token that lets it access your top songs.

Now, you can Query Spotify! Clicking that link takes you to a page that allows you to specify how many songs whose lyrics you want to compare, as well as whether you want those songs chosen from the past few weeks, past few months, or all time. When you click this, the website tells you the specific songs it is going to look at, and then begins the process of finding how the word frequencies compare.

This process usually takes a minute or two, at which point you can click View Data!. This lets you specify whether you want to see the words that are over-represented in your songs or under-represented, and how many of them you’d like to see. After submitting the request, a table is returned with the words and the ratio of their frequencies. For example, 1% of the words in your song lyrics were “dance”, but 0.01% of the words in the reference dataset were “dance”, then you would likely see in the over-represented word page “dance” followed by the ratio between the two, 100.
The data of each query is stored in the database until it is replaced, so each user can check the counts of their previous try until they choose to run another query and replace the data with frequencies from new specifications. 

URL:
https://www.youtube.com/watch?v=Nhu65wDg9s4


