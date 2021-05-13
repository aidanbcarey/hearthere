Fundamentally, the project is a rather simple Python script with orders of magnitude more complicated augmentations to give it a user-friendly interface.  

The specific script is the contents of utils.py with the following functions:

get_freq is a function that takes in Spotify queries, the Genius API object, and a word frequency database. It goes through the list of songs in the Spotify query, gets their lyrics using getlyrics(), finds the frequency of words in all those song lyrics, then for words found in both the songs’ lyrics and the dataset, stores their ratios in the Postgres database.

getlyrics() converts the song title to a more search-friendly format, and then asks the genius API for its lyrics. After a bit of cleaning, it returns the lyrics to the get_freq().

word_count() takes in a string and outputs a dict containing the words in the string as well as the counts for each word. 

This script is the functional backbone of what the project actually does, but there are a number of other functions needed to make using this script as user-friendly as possible. 

Because the Genius API is often quite slow, functions that rely on it should be run in the background to avoid timeouts. This necessitated implementing RQ and redis on Heroku to manage these tasks for me. When get_freq is run in /scrape, the job is sent to a worker to complete, and the user is redirected to another page that can be generated instantly. Once the job is done, the user can then view the data that was generated. 

For both login purposes and data storage, I used a postgres database to store information. Because I have tasks running in the background, it is necessary to use a nice persistent data location from which I can draw information from at my leisure. This required using psycopg2 rather than whatever we used for Finance, which required a number of changes made to the auxiliary functions that existed before. 

I also needed to implement some methods to access the Spotify API. These were basically just ripped from the Python package’s documentation, and are found in /callback and /connect.

The database that I am using to compare word frequencies is not directly from anywhere. I just ran get_freq locally on a Kaggle database containing the titles and artists of the top several hundred songs of the 2010s. It was just to get a somewhat representative sample of what words in popular music tend to be. 
