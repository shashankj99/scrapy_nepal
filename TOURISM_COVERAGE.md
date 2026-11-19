# Nepal tourism questions and data coverage

This is the question inventory for the dataset consumed by the other app. Use it to choose sources and test whether imported records answer what a traveler actually asked.

## Questions to support

| Topic | Questions tourists may ask | Evidence needed |
|---|---|---|
| City trips | What can I do in Kathmandu in one day? Which sights fit a half-day in Patan or Bhaktapur? What can I do near Lakeside in Pokhara when it rains? | Named sights, coordinates, neighborhoods, entrances, hours, fees, and estimated visit duration |
| Local transport | How do I get from the airport to Thamel or Lakeside? Where is the nearest bus stop, taxi stand, or cable car? Can I reach the attraction without a car? | Stops and terminals, walking access, route stops in order, frequency, fare date, and accessible boarding details |
| Intercity transport | How do I travel from Kathmandu to Pokhara, Chitwan, or Lumbini? Where do buses leave? What is the last departure? How do flights, tourist buses, shared jeeps, and private cars compare? | Origin, destination, operator, pickup point, mode, current timetable, fare, and date checked. Safety and reliability claims need their own evidence. |
| Accommodation | Where can I find a hostel in Kathmandu, a hotel by Phewa Lake, a homestay in Bandipur, or a teahouse on a trek? Which options meet my budget or accessibility needs? | Place listings, amenities, accessibility details, and current operator rates and availability |
| Food and nightlife | Where can I try Newari food, dal bhat, or momos? Which places have vegetarian or halal options? Where can I get a beer near Thamel or Lakeside? | Venue, location, cuisine, current menu, dietary information, and opening hours |
| Heritage and culture | What are the major temples, stupas, monasteries, museums, and heritage squares? What are the rules for visiting? When are festivals held? | Site records, official visitor rules, ticket information, and festival dates with calendar year |
| Wildlife and parks | Where can I book a safari in Chitwan or Bardiya? What wildlife might I see and in which season? What are the park entry rules and fees? | Park and entry locations, official access rules, guide and operator details, and season-level species information |
| Trekking and adventure | Where do Annapurna, Everest, Langtang, and Mustang treks start? Which routes suit my time and experience? Can I go boating, paragliding, rafting, or climbing? | Trailheads, route stages, elevation, permits, current conditions, and licensed operators |
| Trip planning | What can I do on a budget, with kids, without stairs, or during monsoon season? Can I combine Kathmandu, Pokhara, and Chitwan in a week? | Travel times, opening hours, season, accessibility, costs, and dated closures |
| Practical needs | Where are information centers, hospitals, pharmacies, ATMs, toilets, or SIM shops? Do I need a visa or permit? Which numbers should I call in an emergency? | Location listings and authoritative, current government or service information |

## Destination groups

The source IDs in [sources.toml](sources.toml) cover approximate map areas. A locality label describes the query area and is not a verified municipal boundary.

| Area | Example questions |
|---|---|
| Kathmandu Valley | What can I see in Thamel, Kathmandu Durbar Square, Patan, and Bhaktapur? Where are museums, temples, cafes, and bus stations? |
| Pokhara | What can I do around Lakeside and Phewa Lake? Where are viewpoints, caves, museums, and places to stay? |
| Chitwan and Bardiya | Where are park facilities and nearby lodges? How do I reach Sauraha or Thakurdwara? |
| Lumbini and Janakpur | Which pilgrimage sites and monasteries can I visit? Where do local buses stop? |
| Bandipur, Ilam, and Rara | Where can I find viewpoints, visitor services, or accommodation? How do I reach each area? |
| Annapurna, Everest and Khumbu, Langtang, and Mustang | Which mapped lodges, visitor sites, airports, and transport points are in the region? What current permits and route conditions should I check? |

Future coverage should include Tansen and Palpa, Gorkha and Manaslu, Nuwakot, Dhorpatan, Dolpo and Shey Phoksundo, Koshi Tappu, eastern trekking regions including Kanchenjunga, and farther-west destinations such as Khaptad and Shuklaphanta. Treat these as expansion targets and validate local names and traveler questions with regional sources.

## What the first import supplies

The [OpenStreetMap dataset](https://www.openstreetmap.org/copyright) discovers named map objects for categories such as lodging, dining, bus stops, bus stations, airports, museums, worship sites, protected areas, viewpoints, lakes, and some adventure venues. Each stored record has a name, category, approximate regional label, and source link. The current schema does not store coordinates, opening hours, routes, prices, menus, availability, or rankings. Listings can be missing or stale, and area overlaps or multiple mapped objects can produce repeats in the consuming app.

## Next source priorities

1. **Destination guides and activities.** Use the [Nepal Tourism Board destination guide](https://ntb.gov.np/en/places-to-go) and [activity guides](https://trade.ntb.gov.np/tourist-activities/city-tours/) to identify destinations and verify background. Confirm reuse terms before importing their text.
2. **Local and intercity journeys.** Use operator or transport-authority feeds for routes, stops, pickup points, fares and timetables. The [Nepal Tourism Board travel FAQ](https://trade.ntb.gov.np/faq) is a discovery reference. Check departure details with the operator.
3. **Fees, rules, and availability.** Use park authorities, heritage site managers, immigration and permit agencies, and listings or feeds supplied by operators. Record the effective date and source of each observation. Show travelers the last verification date for changing information.
4. **Search quality.** Test actual questions across major cities, rural destinations, and trekking regions. Include English and Nepali place names, Romanized spellings, alternate names, and questions where the best response is a clarification. Record unanswered questions to choose the next dataset.
