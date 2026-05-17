using System.Reflection;
using System.Text.Json;
using NotificationApi;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

Storage.Seed();
var processor = new NotificationProcessor();

app.MapPost("/notifications", (CreateNotificationRequest req) =>
{
    var n = Storage.AddNotification(req.TargetChannels, req.Message);
    return Results.Json(n);
});

app.MapGet("/notifications", (HttpRequest request) =>
{
    var statusFilter = request.Query["status"].ToString();
    var searchQuery = request.Query["q"].ToString();
    var notifications = Storage.GetAll().AsEnumerable();

    if (!string.IsNullOrWhiteSpace(statusFilter))
    {
        notifications = notifications.Where(n => string.Equals(n.Status, statusFilter, StringComparison.OrdinalIgnoreCase));
    }

    if (!string.IsNullOrWhiteSpace(searchQuery))
    {
        notifications = notifications.Where(n =>
            n.Message.Contains(searchQuery, StringComparison.OrdinalIgnoreCase)
            || n.TargetChannels.Any(c => c.Value.Contains(searchQuery, StringComparison.OrdinalIgnoreCase))
            || n.TargetChannels.Any(c => c.Type.Contains(searchQuery, StringComparison.OrdinalIgnoreCase))
        );
    }

    var filtered = notifications.ToList();
    var acceptHeaders = request.Headers["Accept"].ToString();
    if (acceptHeaders.Contains("text/html", StringComparison.OrdinalIgnoreCase))
    {
        return Results.Content(RenderNotificationsHtml(filtered, statusFilter, searchQuery), "text/html");
    }
    return Results.Json(filtered);
});

app.MapGet("/notifications/{id:int}", (int id, HttpRequest request) =>
{
    var n = Storage.FindById(id);
    if (n == null) return Results.Json(new { error = "not found" }, statusCode: 404);

    var acceptHeaders = request.Headers["Accept"].ToString();
    if (acceptHeaders.Contains("text/html", StringComparison.OrdinalIgnoreCase))
    {
        return Results.Content(RenderNotificationHtml(n), "text/html");
    }

    return Results.Json(n);
});

app.MapGet("/notifications/retry-failed", (HttpRequest request) =>
{
    var failed = Storage.Notifications
        .Where(n => n.Status == NotificationStatuses.Failed || n.Status == NotificationStatuses.RetryPending)
        .ToList();

    foreach (var n in failed)
    {
        processor.SendOne(n);
    }

    var query = request.QueryString.Value ?? string.Empty;
    return Results.Redirect("/notifications" + query);
});

static string RenderNotificationsHtml(List<Notification> notifications, string selectedStatus, string searchQuery)
{
    string RenderChannels(List<Channel> channels)
    {
        return string.Join("<br>", channels.Select(c => $"<strong>{c.Type}</strong>: {System.Net.WebUtility.HtmlEncode(c.Value)}"));
    }

    string RenderStatusBadge(string status)
    {
        return $"<span class=\"status {status}\">{status}</span>";
    }

    string BuildQuery(string status)
    {
        var items = new List<string>();
        if (!string.IsNullOrWhiteSpace(status)) items.Add($"status={System.Net.WebUtility.UrlEncode(status)}");
        if (!string.IsNullOrWhiteSpace(searchQuery)) items.Add($"q={System.Net.WebUtility.UrlEncode(searchQuery)}");
        return items.Count == 0 ? string.Empty : "?" + string.Join("&", items);
    }

    string RenderFilterButton(string status, string label)
    {
        var active = string.Equals(selectedStatus, status, StringComparison.OrdinalIgnoreCase);
        var css = active ? "filter-button active" : "filter-button";
        var url = "/notifications" + BuildQuery(status);
        return $"<a class=\"{css}\" href=\"{url}\">{label}</a>";
    }

    var total = notifications.Count;
    var pending = notifications.Count(n => n.Status == NotificationStatuses.Pending);
    var retry = notifications.Count(n => n.Status == NotificationStatuses.RetryPending);
    var sent = notifications.Count(n => n.Status == NotificationStatuses.Sent);
    var failed = notifications.Count(n => n.Status == NotificationStatuses.Failed);

    var rows = string.Join("", notifications.Select(n => $"\n        <tr>\n            <td><a class=\"link\" href=\"/notifications/{n.Id}\">#{n.Id}</a></td>\n            <td>{RenderChannels(n.TargetChannels)}</td>\n            <td>{System.Net.WebUtility.HtmlEncode(n.Message)}</td>\n            <td>{RenderStatusBadge(n.Status)}</td>\n            <td>{n.Attempts}</td>\n            <td>{System.Net.WebUtility.HtmlEncode(n.LastError ?? string.Empty)}</td>\n            <td>{n.SmsSegments}</td>\n            <td>{System.Net.WebUtility.HtmlEncode(n.CreatedAt)}</td>\n        </tr>"));

    var html = new System.Text.StringBuilder();
    html.AppendLine("<!DOCTYPE html>");
    html.AppendLine("<html lang=\"en\">");
    html.AppendLine("<head>");
    html.AppendLine("    <meta charset=\"utf-8\">");
    html.AppendLine("    <title>Notifications</title>");
    html.AppendLine("    <style>");
    html.AppendLine("        body { font-family: Inter, system-ui, sans-serif; margin: 0; background: #eef2ff; color: #1f2937; }");
    html.AppendLine("        .page { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }");
    html.AppendLine("        .header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }");
    html.AppendLine("        .title { font-size: 2rem; margin: 0; }");
    html.AppendLine("        .subtitle { color: #4b5563; margin: 6px 0 0; }");
    html.AppendLine("        .metrics { display: flex; flex-wrap: wrap; gap: 12px; }");
    html.AppendLine("        .metric { background: #fff; border: 1px solid #dbeafe; border-radius: 16px; padding: 14px 18px; min-width: 140px; box-shadow: 0 1px 2px rgba(15,23,42,.06); }");
    html.AppendLine("        .metric strong { display: block; font-size: 1.05rem; margin-bottom: 4px; }");
    html.AppendLine("        .filter-bar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 18px; }");
    html.AppendLine("        .filter-button, .refresh-link, .retry-button { display: inline-flex; align-items: center; justify-content: center; padding: 10px 16px; border-radius: 999px; text-decoration: none; font-weight: 700; transition: transform .12s ease, background .12s ease; }");
    html.AppendLine("        .filter-button { background: #eef2ff; color: #1d4ed8; border: 1px solid #dbeafe; }");
    html.AppendLine("        .filter-button.active { background: #4338ca; color: #fff; border-color: #4338ca; }");
    html.AppendLine("        .refresh-link { background: #111827; color: #fff; }");
    html.AppendLine("        .retry-button { background: #f8fafc; color: #1d4ed8; border: 1px solid #dbeafe; }");
    html.AppendLine("        .filter-button:hover, .refresh-link:hover, .retry-button:hover { transform: translateY(-1px); }");
    html.AppendLine("        .search-form { display: inline-flex; gap: 10px; align-items: center; flex-wrap: wrap; }");
    html.AppendLine("        .search-form input { min-width: 220px; padding: 10px 14px; border: 1px solid #c7d2fe; border-radius: 999px; outline: none; }");
    html.AppendLine("        .search-form input:focus { border-color: #4f46e5; box-shadow: 0 0 0 4px rgba(99,102,241,.12); }");
    html.AppendLine("        .search-button { background: #4338ca; color: #fff; border: none; cursor: pointer; border-radius: 999px; padding: 10px 18px; }");
    html.AppendLine("        .search-button:hover { transform: translateY(-1px); }");
    html.AppendLine("        .table-wrap { overflow-x: auto; background: #fff; border-radius: 20px; box-shadow: 0 8px 24px rgba(15,23,42,.08); }");
    html.AppendLine("        table { width: 100%; border-collapse: collapse; min-width: 920px; }");
    html.AppendLine("        th, td { padding: 16px 18px; border-bottom: 1px solid #e5e7eb; text-align: left; }");
    html.AppendLine("        th { background: #4f46e5; color: #fff; font-weight: 700; letter-spacing: .02em; }");
    html.AppendLine("        tbody tr:hover { background: #f8fafc; }");
    html.AppendLine("        .link { color: #4338ca; text-decoration: none; font-weight: 600; }");
    html.AppendLine("        .status { display: inline-flex; align-items: center; justify-content: center; padding: 6px 12px; border-radius: 999px; font-size: 0.9rem; font-weight: 700; text-transform: capitalize; letter-spacing: .01em; }");
    html.AppendLine("        .status.pending { background: #e0f2fe; color: #0369a1; }");
    html.AppendLine("        .status.retry_pending { background: #fef9c3; color: #92400e; }");
    html.AppendLine("        .status.sent { background: #dcfce7; color: #166534; }");
    html.AppendLine("        .status.failed { background: #fee2e2; color: #991b1b; }");
    html.AppendLine("        .small { font-size: 0.92rem; color: #6b7280; }");
    html.AppendLine("    </style>");
    html.AppendLine("</head>");
    html.AppendLine("<body>");
    html.AppendLine("    <div class=\"page\">");
    html.AppendLine("        <div class=\"header\">");
    html.AppendLine("            <div>");
    html.AppendLine("                <h1 class=\"title\">Notification dashboard</h1>");
    html.AppendLine("                <p class=\"subtitle\">A real-time view of stored notifications and their delivery state.</p>");
    html.AppendLine("            </div>");
    html.AppendLine("            <div class=\"metrics\">");
    html.AppendLine("                <div class=\"metric\"><strong>Total</strong>" + total + "</div>");
    html.AppendLine("                <div class=\"metric\"><strong>Pending</strong>" + pending + "</div>");
    html.AppendLine("                <div class=\"metric\"><strong>Retry</strong>" + retry + "</div>");
    html.AppendLine("                <div class=\"metric\"><strong>Sent</strong>" + sent + "</div>");
    html.AppendLine("                <div class=\"metric\"><strong>Failed</strong>" + failed + "</div>");
    html.AppendLine("            </div>");
    html.AppendLine("        </div>");
    html.AppendLine("        <div class=\"filter-bar\">");
    html.AppendLine("            <form class=\"search-form\" action=\"/notifications\" method=\"get\">");
    html.AppendLine("                <input type=\"text\" name=\"q\" value=\"" + System.Net.WebUtility.HtmlEncode(searchQuery) + "\" placeholder=\"Search message, target, or type\" />");
    if (!string.IsNullOrWhiteSpace(selectedStatus))
    {
        html.AppendLine("                <input type=\"hidden\" name=\"status\" value=\"" + System.Net.WebUtility.HtmlEncode(selectedStatus) + "\" />");
    }
    html.AppendLine("                <button class=\"search-button\" type=\"submit\">Search</button>");
    html.AppendLine("            </form>");
    html.AppendLine("            " + RenderFilterButton(string.Empty, "All"));
    html.AppendLine("            " + RenderFilterButton(NotificationStatuses.Pending, "Pending"));
    html.AppendLine("            " + RenderFilterButton(NotificationStatuses.RetryPending, "Retry"));
    html.AppendLine("            " + RenderFilterButton(NotificationStatuses.Sent, "Sent"));
    html.AppendLine("            " + RenderFilterButton(NotificationStatuses.Failed, "Failed"));
    html.AppendLine("            <a class=\"refresh-link\" href=\"/notifications" + BuildQuery(selectedStatus) + "\">Refresh</a>");
    html.AppendLine("            <a class=\"retry-button\" href=\"/notifications/retry-failed" + BuildQuery(selectedStatus) + "\">Retry Failed</a>");
    html.AppendLine("        </div>");
    html.AppendLine("        <div class=\"table-wrap\">");
    html.AppendLine("            <table>");
    html.AppendLine("                <thead>");
    html.AppendLine("                    <tr>");
    html.AppendLine("                        <th>ID</th>");
    html.AppendLine("                        <th>Targets</th>");
    html.AppendLine("                        <th>Message</th>");
    html.AppendLine("                        <th>Status</th>");
    html.AppendLine("                        <th>Attempts</th>");
    html.AppendLine("                        <th>Last Error</th>");
    html.AppendLine("                        <th>SMS Segments</th>");
    html.AppendLine("                        <th>Created At</th>");
    html.AppendLine("                        <th></th>");
    html.AppendLine("                    </tr>");
    html.AppendLine("                </thead>");
    html.AppendLine("                <tbody>");
    html.AppendLine(rows);
    html.AppendLine("                </tbody>");
    html.AppendLine("            </table>");
    html.AppendLine("        </div>");
    html.AppendLine("    </div>");
    html.AppendLine("</body>");
    html.AppendLine("</html>");
    return html.ToString();
}

static string RenderNotificationHtml(Notification n)
{
    string RenderChannels(List<Channel> channels)
    {
        return string.Join("<br>", channels.Select(c => $"<strong>{c.Type}</strong>: {System.Net.WebUtility.HtmlEncode(c.Value)}"));
    }

    string StatusBadge(string status)
    {
        return $"<span class=\"status {status}\">{status}</span>";
    }

    var html = new System.Text.StringBuilder();
    html.AppendLine("<!DOCTYPE html>");
    html.AppendLine("<html lang=\"en\">");
    html.AppendLine("<head>");
    html.AppendLine("    <meta charset=\"utf-8\">");
    html.AppendLine($"    <title>Notification {n.Id}</title>");
    html.AppendLine("    <style>");
    html.AppendLine("        body { font-family: Inter, system-ui, sans-serif; margin: 0; background: #eef2ff; color: #1f2937; }");
    html.AppendLine("        .page { max-width: 900px; margin: 0 auto; padding: 32px 20px; }");
    html.AppendLine("        .card { background: #fff; border-radius: 24px; padding: 28px; box-shadow: 0 18px 40px rgba(15,23,42,.12); }");
    html.AppendLine("        .row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; margin-bottom: 24px; }");
    html.AppendLine("        .row-full { display: block; margin-bottom: 24px; }");
    html.AppendLine("        .label { display: block; font-size: 0.95rem; color: #4b5563; margin-bottom: 8px; }");
    html.AppendLine("        .value { font-size: 1rem; color: #111827; }");
    html.AppendLine("        .status { display: inline-flex; align-items: center; justify-content: center; padding: 8px 14px; border-radius: 999px; font-weight: 700; text-transform: capitalize; letter-spacing: .01em; }");
    html.AppendLine("        .status.pending { background: #e0f2fe; color: #0369a1; }");
    html.AppendLine("        .status.retry_pending { background: #fef9c3; color: #92400e; }");
    html.AppendLine("        .status.sent { background: #dcfce7; color: #166534; }");
    html.AppendLine("        .status.failed { background: #fee2e2; color: #991b1b; }");
    html.AppendLine("        .message-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; white-space: pre-wrap; color: #111827; }");
    html.AppendLine("        .back { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 28px; color: #4338ca; font-weight: 700; text-decoration: none; }");
    html.AppendLine("        .back:hover { text-decoration: underline; }");
    html.AppendLine("    </style>");
    html.AppendLine("</head>");
    html.AppendLine("<body>");
    html.AppendLine("    <div class=\"page\">");
    html.AppendLine("        <a class=\"back\" href=\"/notifications\">← Back to dashboard</a>");
    html.AppendLine("        <div class=\"card\">");
    html.AppendLine("            <div class=\"row-full\">");
    html.AppendLine("                <div class=\"label\">Notification</div>");
    html.AppendLine("                <div class=\"value\"><strong>#" + n.Id + "</strong> · " + StatusBadge(n.Status) + "</div>");
    html.AppendLine("            </div>");
    html.AppendLine("            <div class=\"row\">");
    html.AppendLine("                <div>");
    html.AppendLine("                    <div class=\"label\">Targets</div>");
    html.AppendLine("                    <div class=\"value\">" + RenderChannels(n.TargetChannels) + "</div>");
    html.AppendLine("                </div>");
    html.AppendLine("                <div>");
    html.AppendLine("                    <div class=\"label\">Created at</div>");
    html.AppendLine("                    <div class=\"value\">" + System.Net.WebUtility.HtmlEncode(n.CreatedAt) + "</div>");
    html.AppendLine("                </div>");
    html.AppendLine("            </div>");
    html.AppendLine("            <div class=\"row\">");
    html.AppendLine("                <div>");
    html.AppendLine("                    <div class=\"label\">Attempts</div>");
    html.AppendLine("                    <div class=\"value\">" + n.Attempts + "</div>");
    html.AppendLine("                </div>");
    html.AppendLine("                <div>");
    html.AppendLine("                    <div class=\"label\">SMS segments</div>");
    html.AppendLine("                    <div class=\"value\">" + n.SmsSegments + "</div>");
    html.AppendLine("                </div>");
    html.AppendLine("            </div>");
    html.AppendLine("            <div class=\"row-full\">");
    html.AppendLine("                <div class=\"label\">Message</div>");
    html.AppendLine("                <div class=\"message-card\">" + System.Net.WebUtility.HtmlEncode(n.Message) + "</div>");
    html.AppendLine("            </div>");
    html.AppendLine("            <div class=\"row-full\">");
    html.AppendLine("                <div class=\"label\">Last error</div>");
    html.AppendLine("                <div class=\"value\">" + System.Net.WebUtility.HtmlEncode(n.LastError ?? "No error recorded.") + "</div>");
    html.AppendLine("            </div>");
    html.AppendLine("        </div>");
    html.AppendLine("    </div>");
    html.AppendLine("</body>");
    html.AppendLine("</html>");
    return html.ToString();
}

app.MapPut("/notifications/{id:int}", async (int id, HttpRequest request) =>
{
    var n = Storage.FindById(id);
    if (n == null) return Results.Json(new { error = "not found" }, statusCode: 404);
    var updates = await JsonSerializer.DeserializeAsync<Dictionary<string, JsonElement>>(request.Body);
    foreach (var kvp in updates!)
    {
        var prop = typeof(Notification).GetProperty(kvp.Key, BindingFlags.IgnoreCase | BindingFlags.Public | BindingFlags.Instance);
        if (prop != null && prop.CanWrite)
        {
            var value = kvp.Value.Deserialize(prop.PropertyType, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            prop.SetValue(n, value);
        }
    }
    return Results.Json(n);
});

app.MapPost("/notifications/{id:int}/send", (int id) =>
{
    var n = Storage.FindById(id);
    if (n == null) return Results.Json(new { error = "not found" }, statusCode: 404);
    processor.SendOne(n);
    return Results.Json(n);
});

app.MapPost("/notifications/send-bulk", () =>
{
    processor.SendAll();
    return Results.Json(Storage.GetAll());
});

app.Run("http://localhost:3000");
