import 'dart:math';

const _crockford = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
final _random = Random.secure();

/// A prefix plus 26 Crockford base32 characters, the shape the citizen API
/// accepts for `sos_id` (and uses for `report_id`).
String recordId(String prefix) =>
    '$prefix-${List.generate(26, (_) => _crockford[_random.nextInt(32)]).join()}';
