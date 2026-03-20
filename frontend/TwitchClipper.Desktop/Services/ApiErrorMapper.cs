using System.Net;
using System.Net.Http;
using System.Text.Json;
using TwitchClipper.Desktop.Models;

namespace TwitchClipper.Desktop.Services;

public interface IApiErrorMapper
{
    Task<ApiException> MapFromResponseAsync(HttpResponseMessage response);
}

public sealed class ApiErrorMapper : IApiErrorMapper
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    public async Task<ApiException> MapFromResponseAsync(HttpResponseMessage response)
    {
        var text = await response.Content.ReadAsStringAsync();
        if (response.StatusCode == HttpStatusCode.UnprocessableEntity)
        {
            try
            {
                var payload = JsonSerializer.Deserialize<ApiValidationErrorResponse>(text, JsonOptions);
                var mapped = payload?.Detail.Select(item => item.ToMappedError()).ToList() ?? [];
                return new ApiException(response.StatusCode, "Validation failed.", mapped);
            }
            catch (JsonException)
            {
                return new ApiException(response.StatusCode, "Validation failed with unreadable payload.");
            }
        }

        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return new ApiException(response.StatusCode, "Requested job was not found.");
        }

        if (response.StatusCode == HttpStatusCode.InternalServerError)
        {
            return new ApiException(response.StatusCode, "Server error occurred while processing request.");
        }

        return new ApiException(response.StatusCode, $"Unexpected API error: {(int)response.StatusCode}");
    }
}
