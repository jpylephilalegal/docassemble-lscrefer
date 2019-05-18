A module to assist with referring users with legal problems to legal
services organizations in the United States that are funded by the
Legal Services Corporation (LSC).

# Requirements

The functions in this module (with the exception of
`poverty_percentage()`) require:

* A server-side API key for the [Google Maps Geocoding API], which is
  set in the [Configuration].  This is necessary because the
  `lsc_program_for()` function needs to get the latitude and longitude
  of an address and then see what "service area" contains the point.
* An internet connection.  The functions communicate with LSC's ArcGIS
  service.

# Functions

## `poverty_percentage(household_income, household_size, state)`

The `poverty_percentage()` function returns the percent of poverty of
a household as a decimal number like `150.1`.  The `household_income`
is the total annual income of all members of the household in
dollars.  The `household_size` is the number of adults and children in
the household.  The `state` is the two-letter abbreviation of the
household's state (which is necessary because different scales are
used for Alaska, Hawaii, and other states).

## `lsc_program_for(person)`

The `lsc_program_for()` function returns an `Organization` object with
information about the LSC grantee that serves the area in which the
`person` is located.  The `person` can be an `Individual` or other
object.  `person.address` is expected to be an `Address` object.  The
function identifies the "service area" containing the latitude and
longitude of `person.address`, and then finds the LSC grantee that
has a grant to provide services in that service area.

The attributes defined include:

* `.name.text`: the name of the grantee.
* `.url`: the grantee's web site.
* `.phone_number`: the main phone number of the grantee.
* `.rin`: the recipient information number of the grantee.
* `.serv_a`: the service area ID of the grantee.

## `offices_for(organization, by_proximity_to=None)`

The `offices_for()` function returns a `DAList` of `Address` objects,
each of which represents an office of the given `organization`.

The attributes that are populated for each address object include:

* `.address`
* `.unit` - suite number (if applicable)
* `.city`
* `.state`
* `.zip`
* `.location.longitude`
* `.location.latitude`
* `.office_type` - this is `'Main'` if the office is the grantee's main
  office, or `'Branch'` if it is a branch office.

The `offices_for()` method accepts an optional keyword argument
`by_proximity_to`.  If you call `offices_for(organization,
by_proximity_to=person)`, then the `.distance` attribute of each item
in the `DAList` will be set to the distance in miles between the
`person`'s address and the address of the office.  In addition, the
`DAList` will be sorted in order of which offices are closest in
proximity to the `person`.

## `cities_near(organization, person)`

The `cities_near()` function returns a `DAList` of the unique cities
of the offices of the given `organization`, in order of proximity to
the `person`.

[Google Maps Geocoding API]: https://developers.google.com/maps/documentation/geocoding/intro
[Configuration]: https://docassemble.org/docs/config.html#google
