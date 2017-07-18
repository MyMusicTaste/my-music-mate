# Installation and Usage Instructions for MyMusicMate

## Installation
This installation process is tested on macOS Sierra 10.12.5

### AWS Command Line Interface
First you must download and configure the [AWS Command Line Interface](https://aws.amazon.com/cli/). This will be used for all aws-related activity. (Make sure that you register an AWS account with permissions to CRUD Lambda, SNS, S3, DynamoDB, API Gateway on AWS CLI with `aws configure` command).

## Node.js and Python version
Install Node.js (version 6 or higher) from [here](https://nodejs.org/en/download/), and Python3 (version 3.6.1 or higher) from [here](https://www.python.org/downloads/release/python-361/).

## Serverless framework
Follow the instructions [here](https://serverless.com/framework/docs/providers/aws/guide/installation/) to install the latest version of the Serverless framework by running `npm install -g serverless`.

## Download the source files and Install Requirements
Download MyMusicMate project files from the [Github repo](https://github.com/MyMusicTaste/my-music-mate) and install the requirements by running `pip install -r requirements.txt` and `npm install` on the project root directory. (Make sure the serverless-lex-deploy and serverless-static-s3 plugins are located under the node_modules directory).

### Create your Slack App
- Create a new Slack application and take note of the App Credentials (Client ID, Client Secret, and Verification).
- Create a bot user for your application and give it a username (ex> @mmm).
- Under `OAuth & Permissions`, make sure the following options are listed under `Select Permission Scopes`:
  - `bot; channels:history; channels:read; channels:write; chat:write:bot; chat:write:user`
  
### Configure/Deploy MyMusicTaste
Open the `serverless.yml` configuration file and enter the following information
- `custom: aws: id` - Amazon AWS account number
- `environment : SLACK_APP_ID` - Slack App Client ID (Make sure you wrap the value with ' ' so that the slack app id can be recognized as a string value, not decimal, ex> '189333670117.214221418612').
- `environment : SLACK_APP_SECRET` -  Slack App Client Secret
- `environment : SLACK_APP_TOKEN` -  Slack App VerificationToken 
- `environment : LASTFM_KEY` - LastFM API key.  To obtain, create an API account and request key as per the instructions [here](http://www.last.fm/api).
- `environment : DEVELOPER_KEY` - Google/YouTube API key. To obtain, sign into the Google Developers Console and create an API key as per the instructions [here](https://developers.google.com/youtube/registering_an_application#Create_API_Keys).

Once the configuration file has been updated, execute `sls deploy` to deploy the application to AWS and take note of the generated `install/events/interactives` API endpoints (you can check on the terminal). Then execute `sls lex` to create the Lex bot (There is a slight timing issue on the serverless-lex-deploy plugin, so if you get an error message, please run `sls lex` command 4 or 5 times).

### Update Slack App
- In your Slack application settings under `Event Subscriptions` add your `events` API endpoint as your `Request URL` and subscribe to the <strong>bot events</strong> `message.channels` and `message.im`.
- Under `OAuth & Permissions`, add your `install` API endpoint as your `Redirect URL`.
- Under `Interactive Messages`, add your `interactives` API endpoint as your `Request URL`.
- Add the Slack app to your Slack domain by opening the `install.html` file on the s3 bucket (which you can find the address on the terminal once `sls static` is executed with the name 'Slack App Install Page Link').
  - ! Never install the app via `Install App option` on api.slack.com page because the token won't be saved on your DynamoDB !

At this point MyMusicMate should be fully deployed and ready to help you find a concert! Click the `APPS` button on your slack domain and click `View` MyMusicMate bot, and send direct message (ex><strong> hello~</strong>) to the bot.

If you are having a trouble, feel free to contact me via [jongwonkim@mymusictaste.com](jongwonkim@mymusictaste.com).

## Usage
### Intro/Invite
Using MyMusicMate is a breeze. Simply type a greeting ("Hi," "Hello") and MyMusicMate will give you a short introduction before asking you which friends you'd like to invite to a chatroom. Type one or more usernames and MMM will add them to a queue to be invited. Then let MMM know which channel name you'd like to use.  If you enter an existing channel name, MMM will let you know and prompt you once more for a new channel name.
### Musical Tastes
Once users are gathered, MyMusicMate will ask you to enter your favorite genres or artists to help look for concerts.  You do not have to specify whether your answer is a genre or an artist; MMM will use the Lex slots `Amazon.Artist` and `Amazon.Genre` to figure it out. When you are finished, answer "no" when you are prompted for any more musical preferences. Finally, enter your city in the format `<City>,<State>` and MMM will search for concerts for you and your friends to vote on. If an invalid city is entered, MMM will re-prompt the user for a location.
### Concert Voting
If there were at least 3 concert results that matched your musical tastes, MyMusicMate will now give users a chance to vote for a concert they would like to go to.  Users will be provided with an artist name, venue name, date, as well as a live concert YouTube video to aid in making a decision.  Users have 3 minutes (by default) to vote for a concert. If more time is needed, users may request an extension during the voting process.  If the voting period is almost finished and users have not voted yet, MMM will send them a private message reminding them to vote.

Once voting is complete, MyMusicMate will tally the votes and the next action will vary according to the outcome. If there is a clear winner, MMM will display the concert link for users to purchase tickets.  If a large percentage of users did not like any of the concert options, the unwanted concerts will be discarded and replaced with new options from the concert queue, if they exist.  If votes were split, the least popular concert(s) will be discarded and users will be brought to a second, and final vote.

If the concert queue does not have enough concerts to initiate a vote, users will be prompted to enter new musical preferences and a new concert search will begin.
