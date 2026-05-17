namespace NotificationApi;

public static class SmsSegmenter
{
    // SMS messages are limited to 160 characters per segment (GSM-7).
    public const int MaxSegmentChars = 160;

    // Returns the minimum number of SMS segments needed to deliver `message`
    // without splitting any word across segments. Used to report how many
    // billable SMS parts a notification will consume.
    public static int MinSegments(string message)
    {
        if (string.IsNullOrWhiteSpace(message)) return 0;
        var words = message.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (words.Length == 0) return 0;

        var n = words.Length;
        var dp = new int[n + 1];
        for (int i = 0; i <= n; i++) dp[i] = int.MaxValue;
        dp[n] = 0;

        for (int i = n - 1; i >= 0; i--)
        {
            int currentLen = 0;
            for (int j = i; j < n; j++)
            {
                var wordLen = words[j].Length;
                if (wordLen > MaxSegmentChars)
                {
                    currentLen = int.MaxValue;
                    break;
                }

                currentLen = currentLen == 0 ? wordLen : currentLen + 1 + wordLen;
                if (currentLen > MaxSegmentChars) break;

                if (dp[j + 1] != int.MaxValue)
                {
                    dp[i] = Math.Min(dp[i], dp[j + 1] + 1);
                }
            }
        }

        return dp[0] == int.MaxValue ? 0 : dp[0];
    }
}
