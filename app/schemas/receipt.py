from pydantic import BaseModel, Field


class Item(BaseModel):
    item: str = Field(..., alias="Item", description="Name of the purchased item")
    quantity: int = Field(..., alias="Quantity", description="Quantity purchased")
    price: float = Field(..., alias="Price", description="Unit price of the item")

    model_config = {"populate_by_name": True}


class ServiceProvider(BaseModel):
    name: str = Field(..., alias="Name")
    address: str | None = Field(None, alias="Address")
    vat_number: str | None = Field(None, alias="VATNumber")

    model_config = {"populate_by_name": True}


class TransactionDetails(BaseModel):
    items: list[Item] = Field(default_factory=list, alias="Items")
    currency: str | None = Field(None, alias="Currency")
    total_amount: float | None = Field(None, alias="TotalAmount")
    vat: str | None = Field(None, alias="VAT")

    model_config = {"populate_by_name": True}


class ReceiptResponse(BaseModel):
    service_provider: ServiceProvider = Field(..., alias="ServiceProvider")
    transaction_details: TransactionDetails = Field(..., alias="TransactionDetails")
    message: str | None = Field(None, alias="Message", description="Informational message about the parsing process")

    model_config = {"populate_by_name": True}


class BatchReceiptResult(BaseModel):
    """Result for a single file within a batch request."""
    filename: str = Field(..., alias="Filename")
    success: bool = Field(..., alias="Success")
    data: ReceiptResponse | None = Field(None, alias="Data")
    error: str | None = Field(None, alias="Error")

    model_config = {"populate_by_name": True}


class BatchReceiptResponse(BaseModel):
    """Response for the batch processing endpoint."""
    total: int = Field(..., alias="Total")
    successful: int = Field(..., alias="Successful")
    failed: int = Field(..., alias="Failed")
    results: list[BatchReceiptResult] = Field(..., alias="Results")

    model_config = {"populate_by_name": True}
