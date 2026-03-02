import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

// --- KONFIGURATION ---
final String githubOrg = Platform.environment['GITHUB_ORG'] ?? '';
final String token = Platform.environment['GH_TOKEN'] ?? '';
final Map<String, String> headers = {
  'Authorization': 'token $token',
  'Accept': 'application/vnd.github.v3+json',
};

const String readmePath = 'profile/README.md';

class Course {
  final String title;
  final String longTitle;
  final String type;
  final String year;
  final String grade;
  final String campNumber;
  final String url;

  Course({
    required this.title,
    required this.longTitle,
    required this.type,
    required this.year,
    required this.grade,
    required this.campNumber,
    required this.url,
  });

  // Getter til at bestemme kategorien
  String get category =>
      type.toLowerCase().contains('aspirant') ? 'Aspirant' : 'Folkeskole';

  // Getter til Folkeskole visning
  String get folkeskoleDisplay => "$grade. klasse, camp $campNumber";

  factory Course.fromJson(Map<String, dynamic> json, String repoUrl) {
    return Course(
      title: json['display_name'] ?? 'Navn mangler',
      longTitle:
          json['long_display_name'] ?? json['display_name'] ?? 'Navn mangler',
      type: json['type'] ?? 'Andet',
      year: json['year']?.toString() ?? 'Ukendt år',
      grade: json['grade']?.toString() ?? '?',
      campNumber: json['camp_number']?.toString() ?? '?',
      url: repoUrl,
    );
  }
}

Future<List<Course>> getCourseData() async {
  List<Course> allCourses = [];
  int page = 1;

  while (true) {
    final reposUrl =
        'https://api.github.com/orgs/$githubOrg/repos?per_page=100&page=$page';
    final response = await http.get(Uri.parse(reposUrl), headers: headers);

    if (response.statusCode != 200) break;

    final List repos = jsonDecode(response.body);
    if (repos.isEmpty) break;

    for (var repo in repos) {
      final metaUrl =
          'https://api.github.com/repos/$githubOrg/${repo['name']}/contents/meta.json';
      final metaRes = await http.get(Uri.parse(metaUrl), headers: headers);

      if (metaRes.statusCode == 200) {
        try {
          final metaJson = jsonDecode(metaRes.body);
          // GitHub base64 koder indholdet, vi skal dekode det
          final content = utf8.decode(
            base64.decode(metaJson['content'].replaceAll('\n', '')),
          );
          final Map<String, dynamic> metaData = jsonDecode(content);

          allCourses.add(Course.fromJson(metaData, repo['html_url']));
        } catch (e) {
          print('Fejl ved parsing af meta.json i ${repo['name']}: $e');
        }
      }
    }
    page++;
  }
  return allCourses;
}

String buildMarkdown(List<Course> courses) {
  // Struktur: Type -> År -> Liste af kurser
  Map<String, Map<String, List<Course>>> tree = {};

  for (var c in courses) {
    tree.putIfAbsent(c.category, () => {});
    tree[c.category]!.putIfAbsent(c.year, () => []);
    tree[c.category]![c.year]!.add(c);
  }

  var sb = StringBuffer("# Kursus Arkiv\n\n");

  // Sorter Typer
  var sortedTypes = tree.keys.toList()..sort();
  for (var type in sortedTypes) {
    sb.writeln("## $type\n");

    // Sorter År (nyeste først)
    var sortedYears = tree[type]!.keys.toList()..sort((a, b) => b.compareTo(a));
    for (var year in sortedYears) {
      sb.writeln("<details>\n  <summary><h3>Årstal: $year</h3></summary>\n");

      var coursesInYear = tree[type]![year]!;

      if (type == "Aspirant") {
        // Grupper efter Samling
        Map<String, List<Course>> camps = {};
        for (var c in coursesInYear) {
          String campName = "Samling ${c.campNumber}";
          camps.putIfAbsent(campName, () => []);
          camps[campName]!.add(c);
        }

        var sortedCamps = camps.keys.toList()..sort();
        for (var camp in sortedCamps) {
          sb.writeln("  <details style='margin-left: 20px;'>");
          sb.writeln("    <summary><h4>$camp</h4></summary>\n");
          for (var c in camps[camp]!) {
            sb.writeln("    * [${c.title}](${c.url})");
          }
          sb.writeln("  </details>");
        }
      } else {
        // Folkeskole: Sorter efter longTitle
        coursesInYear.sort((a, b) => a.longTitle.compareTo(b.longTitle));
        for (var c in coursesInYear) {
          sb.writeln(
            "  * [${c.longTitle}](${c.url}) — *${c.folkeskoleDisplay}*",
          );
        }
      }
      sb.writeln("</details>\n");
    }
    sb.writeln("---\n");
  }
  return sb.toString();
}

void main() async {
  if (githubOrg.isEmpty || token.isEmpty) {
    print('Fejl: GITHUB_ORG eller GH_TOKEN mangler i environment.');
    exit(1);
  }

  print('Henter data fra GitHub...');
  final data = await getCourseData();

  print('Bygger Markdown...');
  final markdown = buildMarkdown(data);

  print('Gemmer til $readmePath...');
  final file = File(readmePath);
  await file.parent.create(recursive: true);
  await file.writeAsString(markdown);

  print('Succes!');
}
