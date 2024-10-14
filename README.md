# Mindtools
_Logic-driven web content creation kit_

Mindtools source code is based on Serafin and was then upgraded in several steps. 
It is a Django-based web platform that gives content builders a set of flexible building blocks for creating logic-driven sites. Examples include:

- בWeb forms and questionaires
- Self-help programs
- E-learning programs
- Dynamic websites with a complex underlying logic

The main features in this content management system can be divded into (1) the way content is desigend to interact with the user and (2) administrative capabilities.

**(1) Content:**
 Content is presented to a user in either a webpage, text message, whatsapp message, or email
- eLearning UI: The program builder can design web-pages to appear as part of a learning module that users can navigate through back anf forth. Once a module is complete the user can go back and read it in a different subsection in the menu.
- Tools can be presented to users through the menu once they are made available. They include audio, video, and doccuments.
- Program flow is controlled on different levels. Sessions are built as a series of pages or other events (e-mail, SMS), allowing the users' path to be controlled by logic applied to their choices. Sessions may be put into sequence, where registered users are invited to follow the Program day by day, or sessions may be accessed manually. Pages and other content may present text, media, or forms for the user to fill out.

**(2) Administrative capabilities**
- Different levels of users (with more that can be administered using the platform). Levels include administrative, program manager (who sees only one program and manage its content and uders), therapist (who access a therpaist dashboard to view user state and to message the user), and end-users.
- Therapsit dashboard provides information on the users (program usage, and completed questionnaires), alerts presented to the therpaist (as they were desiigned in the program flow/sessions), and a location to write down notes to users.
- Programs can be imported or exported to be used in a different server.

Originally, Serafin was developed by [Inonit AS](http://inonit.no/) for [SERAF](http://www.med.uio.no/klinmed/english/research/centres/seraf/), the Norwegian Centre for Addiction Research at the University of Oslo, in order for them to create a program to help users stop smoking while gathering research data on the efficacy of therapeutic techniques. 
Mindtools was then upgraded in several stepsby, by an independant contractor and then by DrorSoft, for the Digital Interventions Psychology lab at the University of Haifa.

## Getting started

The preferred method for setting up Mindtools for development is through docker-compose. A complete environment is provided, including PostgreSQL, Redis, and a Python container with a Django development server and a Huey task runner.

Install [docker](https://docs.docker.com/engine/installation/) and [docker-compose](https://docs.docker.com/compose/install/).

Run docker-compose to build the environment:

    $ docker-compose up

In a separate terminal, run database migrations (first time, but may be needed after model changes):

    $ docker-compose exec app ./manage.py migrate 

Create a local admin user (first time only):

    $ docker-compose exec app ./manage.py createsuperuser

Run tests with:

    $ docker-compose exec app ./manage.py test

You may run other Django management commands the same way.


## Contributing

Mindtools was last updated in the summer of 2024.

Pull requests are welcome.


## License

The source code for this project is licensed under the AGPL v3 license, see [LICENSE.txt](LICENSE.txt) for details.

Original Serafin version Copyright (C) 2018 Institute of Clinical Medicine, University of Oslo. 
Subsequent versions were developed by Gal Weizenberg and then DrorSoft used by University of Haifa.
All rights reserved. 
