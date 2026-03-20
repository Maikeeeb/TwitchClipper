/*
Test Plan
- Partitions: run-next union response shapes
- Boundaries: processed=0 omits fields, processed=1 requires fields
- Failure modes: invalid union should raise ApiException
# Covers: UI-IMPL-045
*/

using System.Net;
using System.Net.Http;
using System.Text;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests;

public class ApiClientContractTests
{
    [Fact]
    public async Task RunNext_processed_zero_is_accepted()
    {
        // Why: union contract must allow processed=0 shape.
        using var client = BuildClient("{\"processed\":0}");
        var sut = new ApiClient(client, new ApiErrorMapper());

        var result = await sut.RunNextAsync();

        Assert.Equal(0, result.Processed);
        Assert.True(result.IsUnionValid());
    }

    [Fact]
    public async Task RunNext_invalid_union_throws()
    {
        // Why: invalid response must be rejected to avoid undefined UI state.
        using var client = BuildClient("{\"processed\":1}");
        var sut = new ApiClient(client, new ApiErrorMapper());

        await Assert.ThrowsAsync<ApiException>(() => sut.RunNextAsync());
    }

    private static HttpClient BuildClient(string payload)
    {
        var handler = new StaticHandler(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(payload, Encoding.UTF8, "application/json")
        });

        return new HttpClient(handler)
        {
            BaseAddress = new Uri("http://localhost:8000")
        };
    }

    private sealed class StaticHandler : HttpMessageHandler
    {
        private readonly HttpResponseMessage _response;

        public StaticHandler(HttpResponseMessage response)
        {
            _response = response;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromResult(_response);
        }
    }
}
