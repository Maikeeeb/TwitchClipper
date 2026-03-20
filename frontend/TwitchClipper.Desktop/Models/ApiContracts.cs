using System.Text.Json;
using System.Text.Json.Serialization;

namespace TwitchClipper.Desktop.Models;

public sealed class VodHighlightsJobRequestDto
{
    public string VodUrl { get; set; } = string.Empty;

    public string OutputDir { get; set; } = string.Empty;

    public List<string> Keywords { get; set; } = [];

    public string? ChatPath { get; set; }

    public int MinCount { get; set; } = 3;

    public int SpikeWindowSeconds { get; set; } = 30;

    public int SegmentPaddingSeconds { get; set; } = 12;

    public double MaxSegmentSeconds { get; set; } = 120;

    public int DiversityWindows { get; set; } = 8;
}

public sealed class ClipMontageJobRequestDto
{
    public List<string> StreamerNames { get; set; } = [];

    public string CurrentVideosDir { get; set; } = string.Empty;

    public bool ApplyOverlay { get; set; }

    public int? MaxClips { get; set; }

    public int? ScrapePoolSize { get; set; }

    public int? PerStreamerK { get; set; }
}

public sealed class JobSubmitResponseDto
{
    public string JobId { get; set; } = string.Empty;
}

public sealed class HealthResponseDto
{
    public bool Ok { get; set; }
}

public sealed class RunNextResponseDto
{
    public int Processed { get; set; }

    public string? JobId { get; set; }

    public string? Status { get; set; }

    public bool IsUnionValid()
    {
        if (Processed == 0)
        {
            return string.IsNullOrWhiteSpace(JobId) && string.IsNullOrWhiteSpace(Status);
        }

        return Processed == 1
            && !string.IsNullOrWhiteSpace(JobId)
            && !string.IsNullOrWhiteSpace(Status);
    }
}

public sealed class JobResponseDto
{
    public string Id { get; set; } = string.Empty;

    public string Type { get; set; } = string.Empty;

    public string Status { get; set; } = string.Empty;

    public double Progress { get; set; }

    public string? CreatedAt { get; set; }

    public string? StartedAt { get; set; }

    public string? FinishedAt { get; set; }

    public string? Error { get; set; }

    public JsonElement? Result { get; set; }

    public JsonElement? Outputs { get; set; }

    public Dictionary<string, JsonElement> Params { get; set; } = [];
}

public sealed class VodHighlightsResultDto
{
    public string? VodPath { get; set; }

    public string? ChatPath { get; set; }

    public int? SegmentsCount { get; set; }

    public int? ClipsCount { get; set; }

    public string? MontagePath { get; set; }

    public string? ClipsDir { get; set; }

    public string? MetadataPath { get; set; }

    public JsonElement? DurationsS { get; set; }
}

public sealed class ClipMontageResultDto
{
    public List<string> Paths { get; set; } = [];

    public int Count { get; set; }
}

public sealed class ApiValidationError
{
    public string Field { get; set; } = string.Empty;

    public string Message { get; set; } = string.Empty;
}

public sealed class ApiValidationErrorResponse
{
    public List<ApiValidationErrorDetail> Detail { get; set; } = [];
}

public sealed class ApiValidationErrorDetail
{
    public List<JsonElement> Loc { get; set; } = [];

    public string Msg { get; set; } = string.Empty;

    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("input")]
    public JsonElement Input { get; set; }

    public ApiValidationError ToMappedError()
    {
        var field = string.Empty;
        if (Loc.Count > 0)
        {
            field = string.Join('.', Loc.Where(item => item.ValueKind == JsonValueKind.String).Select(item => item.GetString()));
        }

        return new ApiValidationError
        {
            Field = field,
            Message = Msg,
        };
    }
}
