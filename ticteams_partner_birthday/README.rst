==============
User Birthday
==============

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3
.. |badge2| image:: https://img.shields.io/badge/odoo-18.0-714B67.png
    :target: https://www.odoo.com/documentation/18.0/
    :alt: Odoo 18.0

|badge1| |badge2|

Track and celebrate your team's birthdays directly inside Odoo.

This module adds a **Birthday** field on internal users (``res.users``) and
provides a dedicated *Birthdays* menu where everyone is sorted by their
upcoming celebration date.  A daily scheduled action automatically detects
users whose birthday matches the current day and pushes a real-time popup
notification (via the bus) to every internal user, plus a chatter message
on the celebrant's record.

Features
========

* **Birthday field** on every internal user, with validation (no future
  dates) and tracking.
* **Computed fields**: next birthday, days remaining, current age, and
  a boolean flag ``is_birthday_today`` (all stored, so they can be used in
  filters and groupings).
* **Birthdays menu** with:

  - *List view* sorted by the upcoming celebration date, with colour
    decorations for "today" and "next 7 days".
  - *Kanban view* highlighting today's celebrants.
  - *Filters*: today, this week, within 30 days, set / missing.
  - *Group by month*.
* **Daily cron** ``User Birthday: Daily Notification`` that fires the
  bus notifications.
* **Manual action** from the user form: *Send birthday notification now*.
* Designed for Odoo 18.0, ready for the Odoo Apps Store.

Configuration
=============

No configuration is required.  After installing the module:

#. Open *Settings → Users & Companies → Users* (or the new *Birthdays* menu).
#. Edit any internal user and set the *Birthday* field on the *Birthday*
   tab.
#. The *Birthdays* menu will then list everyone ordered by upcoming
   celebration date.

The cron *User Birthday: Daily Notification* runs once a day.  You can
adjust its frequency or run it manually from
*Settings → Technical → Automation → Scheduled Actions*.

Usage
=====

* Open the *Birthdays* application from the main menu to see all users
  ordered by their next birthday.
* Use the search filters to narrow the list to today, this week, or
  within the next 30 days.
* When the daily cron runs and detects a birthday, every connected
  internal user receives a real-time popup notification (sticky, success
  style).
* Use the *Send birthday notification now* button on a user's form to
  trigger a notification on demand.

Bug Tracker
===========

Please report issues or feature requests through the project's official
support channel.

Credits
=======

* TICTeams

Maintainer
----------

This module is maintained by **TICTeams**.
