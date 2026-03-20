/*
Test Plan
- Partitions: 422 validation payloads, known status mapping, default fallback mapping
- Boundaries: empty validation detail list and unreadable json body
- Failure modes: malformed 422 payload still returns safe ApiException
# Covers: UI-IMPL-050
*/

using System.Net;
using System.Net.Http;
using System.Text;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests;

public class ApiErrorMapperTests
{
    [Fact]
    public async Task Map_422_validation_payload_maps_field_errors()
    {
        // Why: UI validation rendering depends on mapped detail fields and messages.
        const string payload = """
            {
              "detail": [
                { "loc": ["body", "vod_url"], "msg": "Field required", "type": "missing", "input": null }
              ]
            }
            """;
        var mapper = new ApiErrorMapper();

        var result = await mapper.MapFromResponseAsync(BuildResponse(HttpStatusCode.UnprocessableEntity, payload));

        Assert.Equal(HttpStatusCode.UnprocessableEntity, result.StatusCode);
        Assert.Equal("Validation failed.", result.Message);
        Assert.Single(result.ValidationErrors);
        Assert.Equal("body.vod_url", result.ValidationErrors[0].Field);
    }

    [Fact]
    public async Task Map_422_malformed_payload_returns_unreadable_message()
    {
        // Why: malformed server payloads should degrade to a deterministic user-safe message.
        var mapper = new ApiErrorMapper();

        var result = await mapper.MapFromResponseAsync(
            BuildResponse(HttpStatusCode.UnprocessableEntity, "{not-json"));

        Assert.Equal("Validation failed with unreadable payload.", result.Message);
        Assert.Empty(result.ValidationErrors);
    }

    [Fact]
    public async Task Map_not_found_and_server_error_use_specific_messages()
    {
        // Why: known status codes must map to actionable, stable text for UI banners.
        var mapper = new ApiErrorMapper();

        var notFound = await mapper.MapFromResponseAsync(BuildResponse(HttpStatusCode.NotFound, "{}"));
        var serverError = await mapper.MapFromResponseAsync(
            BuildResponse(HttpStatusCode.InternalServerError, "{}"));

        Assert.Equal("Requested job was not found.", notFound.Message);
        Assert.Equal("Server error occurred while processing request.", serverError.Message);
    }

    [Fact]
    public async Task Map_unknown_status_uses_numeric_fallback_message()
    {
        // Why: unknown API failures should still include the status code for diagnosis.
        var mapper = new ApiErrorMapper();

        var result = await mapper.MapFromResponseAsync(BuildResponse(HttpStatusCode.BadGateway, "{}"));

        Assert.Equal("Unexpected API error: 502", result.Message);
    }

    private static HttpResponseMessage BuildResponse(HttpStatusCode code, string payload)
    {
        return new HttpResponseMessage(code)
        {
            Content = new StringContent(payload, Encoding.UTF8, "application/json"),
        };
    }
}
