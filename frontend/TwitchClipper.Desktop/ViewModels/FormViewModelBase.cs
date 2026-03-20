using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public abstract class FormViewModelBase : ViewModelBase
{
    private bool _isDirty;
    private bool _isSubmitting;

    protected readonly IDialogService DialogService;

    protected FormViewModelBase(IDialogService dialogService)
    {
        DialogService = dialogService;
    }

    public bool IsDirty
    {
        get => _isDirty;
        protected set => SetProperty(ref _isDirty, value);
    }

    public bool IsSubmitting
    {
        get => _isSubmitting;
        protected set => SetProperty(ref _isSubmitting, value);
    }

    public bool ConfirmCancelIfDirty()
    {
        if (!IsDirty)
        {
            return true;
        }

        return DialogService.ConfirmDiscardChanges();
    }

    protected void MarkDirty()
    {
        IsDirty = true;
    }
}
