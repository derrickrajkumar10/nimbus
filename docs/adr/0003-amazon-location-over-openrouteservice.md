# Routing uses Amazon Location Routes v2, not OpenRouteService

The design lock defaulted to OpenRouteService, but it has no two-wheeler profile, so two-wheelers would be routed as cars. Amazon Location Routes v2 has a `Scooter` travel mode and polygon avoidance. Two-wheelers map to `Scooter`, and cars and ambulances map to `Car`. Its avoidance is best-effort, so the router must check the response's violation flag and return "no safe route" rather than a route through a no-go zone.
