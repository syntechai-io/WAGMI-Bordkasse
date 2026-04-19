// CrewLogWidget.swift — WidgetKit extension target.
//
// Drop this file into a new "Widget Extension" target in Xcode named
// "CrewLogWidget". Bundle ID suggestion: app.crewlog.mobile.widget
// Required entitlements:
//   - App Group: group.app.crewlog.mobile
//   - Keychain Sharing access group: $(AppIdentifierPrefix)app.crewlog.mobile
//
// The host app stores the bearer token in the shared Keychain via
// @aparajita/capacitor-secure-storage; see ios_app/README_IOS.md for the
// step-by-step Xcode setup.

import WidgetKit
import SwiftUI

// MARK: - Snapshot model

struct CrewLogSnapshot: Decodable {
    struct TripInfo: Decodable {
        let id: Int
        let name: String
        let day: Int?
    }
    struct Totals: Decodable {
        let distance_nm: Double
        let motor_hours: Double
    }
    struct LastEntry: Decodable {
        let at: String?
        struct Position: Decodable { let lat: Double; let lon: Double }
        let position: Position?
    }
    let v: Int
    let state: String
    let trip: TripInfo?
    let totals: Totals?
    let last_entry: LastEntry?
}

// MARK: - Keychain helper (shared App Group access group)

enum WidgetKeychain {
    static let accessGroup = "group.app.crewlog.mobile"

    private static func makeQuery(_ key: String) -> [String: Any] {
        return [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecAttrAccessGroup as String: accessGroup,
            kSecAttrSynchronizable as String: false,
        ]
    }

    static func read(_ key: String) -> String? {
        var q = makeQuery(key)
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        q[kSecReturnData as String] = true
        var item: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}

// MARK: - Timeline provider

struct CrewLogEntry: TimelineEntry {
    let date: Date
    let snapshot: CrewLogSnapshot?
    let error: String?
}

struct CrewLogProvider: TimelineProvider {
    func placeholder(in context: Context) -> CrewLogEntry {
        CrewLogEntry(date: Date(), snapshot: nil, error: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (CrewLogEntry) -> Void) {
        fetch { entry in completion(entry) }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<CrewLogEntry>) -> Void) {
        fetch { entry in
            // Refresh roughly every 20 minutes; iOS will smooth out the budget.
            let next = Date().addingTimeInterval(20 * 60)
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }

    private func fetch(completion: @escaping (CrewLogEntry) -> Void) {
        guard
            let token = WidgetKeychain.read("crewlog.widget.token"),
            let baseUrl = WidgetKeychain.read("crewlog.widget.baseUrl"),
            let url = URL(string: baseUrl + "/api/widget/snapshot")
        else {
            completion(CrewLogEntry(date: Date(), snapshot: nil, error: "not_configured"))
            return
        }
        var req = URLRequest(url: url, timeoutInterval: 10)
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        URLSession.shared.dataTask(with: req) { data, resp, err in
            if let err = err {
                completion(CrewLogEntry(date: Date(), snapshot: nil, error: err.localizedDescription))
                return
            }
            if let http = resp as? HTTPURLResponse, http.statusCode == 401 {
                completion(CrewLogEntry(date: Date(), snapshot: nil, error: "unauthorized"))
                return
            }
            guard let data = data,
                  let snap = try? JSONDecoder().decode(CrewLogSnapshot.self, from: data) else {
                completion(CrewLogEntry(date: Date(), snapshot: nil, error: "decode_failed"))
                return
            }
            completion(CrewLogEntry(date: Date(), snapshot: snap, error: nil))
        }.resume()
    }
}

// MARK: - Views

struct CrewLogSmallView: View {
    let entry: CrewLogEntry
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "sailboat.fill")
                    .font(.system(size: 14, weight: .bold))
                Text("CrewLog")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.secondary)
            }
            Spacer(minLength: 0)
            content
        }
        .padding(12)
    }

    @ViewBuilder
    private var content: some View {
        if entry.error == "unauthorized" {
            Text("Open CrewLog\nto sign in").font(.system(size: 13, weight: .medium))
        } else if let snap = entry.snapshot, snap.state == "ok", let trip = snap.trip {
            Text(trip.name).font(.system(size: 14, weight: .bold)).lineLimit(1)
            if let day = trip.day, let totals = snap.totals {
                Text("Day \(day) · \(formatNm(totals.distance_nm)) nm")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.secondary)
            }
            if let last = snap.last_entry?.at, let h = formatHM(last) {
                Text("Last: \(h)").font(.system(size: 11)).foregroundColor(.secondary)
            }
        } else {
            Text("Open CrewLog\nto start a trip").font(.system(size: 13, weight: .medium))
        }
    }
}

struct CrewLogMediumView: View {
    let entry: CrewLogEntry
    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            CrewLogSmallView(entry: entry)
                .frame(maxWidth: .infinity, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                Text("Position").font(.system(size: 11, weight: .semibold)).foregroundColor(.secondary)
                if let pos = entry.snapshot?.last_entry?.position {
                    Text(String(format: "%.3f, %.3f", pos.lat, pos.lon))
                        .font(.system(size: 12, weight: .medium).monospacedDigit())
                } else {
                    Text("—").font(.system(size: 12)).foregroundColor(.secondary)
                }
                Spacer(minLength: 8)
                Text("Engine").font(.system(size: 11, weight: .semibold)).foregroundColor(.secondary)
                if let h = entry.snapshot?.totals?.motor_hours {
                    Text(String(format: "%.1f h", h))
                        .font(.system(size: 12, weight: .medium).monospacedDigit())
                } else {
                    Text("—").font(.system(size: 12)).foregroundColor(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 12)
            .padding(.trailing, 12)
        }
    }
}

private func formatNm(_ v: Double) -> String {
    String(format: "%.0f", v)
}

private func formatHM(_ iso: String) -> String? {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    let date = f.date(from: iso) ?? ISO8601DateFormatter().date(from: iso)
    guard let d = date else { return nil }
    let df = DateFormatter()
    df.dateFormat = "HH:mm"
    return df.string(from: d)
}

// MARK: - Widget configuration

struct CrewLogWidgetEntryView: View {
    @Environment(\.widgetFamily) var family
    var entry: CrewLogEntry
    var body: some View {
        switch family {
        case .systemMedium:
            CrewLogMediumView(entry: entry)
        default:
            CrewLogSmallView(entry: entry)
        }
    }
}

@main
struct CrewLogWidget: Widget {
    let kind: String = "CrewLogWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: CrewLogProvider()) { entry in
            CrewLogWidgetEntryView(entry: entry)
                .widgetURL(URL(string: "crewlog://logbook/today"))
        }
        .configurationDisplayName("CrewLog")
        .description("Active trip at a glance.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
