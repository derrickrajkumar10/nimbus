import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

const _key = 'install_id';

/// This install's anonymous identity (`X-Install-Id`): `inst-` plus 32 hex
/// characters, made once and kept. 37 characters meets the API's 8–80 rule.
Future<String> loadInstallId(SharedPreferences p) async {
  final stored = p.getString(_key);
  if (stored != null) return stored;
  final id = 'inst-${const Uuid().v4().replaceAll('-', '')}';
  await p.setString(_key, id);
  return id;
}
