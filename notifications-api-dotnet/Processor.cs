using NotificationApi.Providers;

namespace NotificationApi;

public class NotificationProcessor
{
    private static readonly Dictionary<string, Func<Dictionary<string, string>, ProviderResponse>> ProviderSenders =
        new(StringComparer.OrdinalIgnoreCase)
        {
            { "email", EmailProvider.Send },
            { "sms", SmsProvider.Send },
            { "push", PushProvider.Send }
        };

    public void SendOne(Notification n)
    {
        n.Status = NotificationStatuses.Processing;
        n.Attempts += 1;
        n.LastAttemptAt = DateTime.Now.ToString("O");

        if (n.TargetChannels.Count == 0)
        {
            n.Status = NotificationStatuses.Failed;
            n.LastError = "No target channels";
            return;
        }

        var results = new List<ProviderResponse>();
        foreach (var channel in n.TargetChannels)
        {
            if (!ProviderSenders.TryGetValue(channel.Type, out var sender))
            {
                results.Add(new ProviderResponse
                {
                    Result = "InvalidRequest",
                    ErrorCode = "UNKNOWN_CHANNEL",
                    Message = $"[{channel.Type}] unknown channel"
                });
                continue;
            }

            var req = new Dictionary<string, string>
            {
                { "recipient", channel.Value },
                { "message", n.Message }
            };

            results.Add(sender(req));
        }

        n.LastError = string.Join(" | ", results.Select(r => r.Message));

        var anySuccess = results.Any(r => r.Result == "Success");
        var anyTemporary = results.Any(r => r.Result == "TemporaryFailure");
        var anyPermanent = results.Any(r => r.Result == "PermanentFailure");

        if (anySuccess && !anyTemporary)
        {
            n.Status = NotificationStatuses.Sent;
        }
        else if (anyTemporary)
        {
            n.Status = NotificationStatuses.RetryPending;
        }
        else if (anyPermanent || results.Any(r => r.Result == "InvalidRequest"))
        {
            n.Status = NotificationStatuses.Failed;
        }
        else
        {
            n.Status = NotificationStatuses.Failed;
        }
    }

    public void SendAll()
    {
        var pending = Storage.Notifications
            .Where(n => n.Status == NotificationStatuses.Pending || n.Status == NotificationStatuses.RetryPending)
            .ToList();

        foreach (var n in pending)
        {
            SendOne(n);
        }
    }
}
