using System.Net;
using TwitchClipper.Desktop.Models;

namespace TwitchClipper.Desktop.Services;

public sealed class ApiException : Exception
{
    public ApiException(HttpStatusCode? statusCode, string message, List<ApiValidationError>? validationErrors = null)
        : base(message)
    {
        StatusCode = statusCode;
        ValidationErrors = validationErrors ?? [];
    }

    public HttpStatusCode? StatusCode { get; }

    public IReadOnlyList<ApiValidationError> ValidationErrors { get; }
}
