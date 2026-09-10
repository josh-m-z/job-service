from pydantic import BaseModel, model_validator
from typing import Literal
from uuid import UUID


class JobCreate(BaseModel):

    job_type: Literal["simulate_work", "sum_numbers", "fail_then_succeed", "process_document"]
    payload: dict
    idempotency_key: str | None = None


    @model_validator(mode="after") # a model checker for the recently created object, checks more specific requirments
    def validate_payload(self): # self becomes job object
        if self.job_type == "simulate_work": # check that under specific condiotns, the model is valid
            if "seconds" not in self.payload:
                raise ValueError(
                    "simulate_work payload must contain 'seconds'"
                )

            if not isinstance(self.payload["seconds"], (int, float)):
                raise ValueError(
                    "'seconds' must be a number"
                )

            if self.payload["seconds"] <= 0:
                raise ValueError(
                    "'seconds' must be greater than 0"
                )

        elif self.job_type == "sum_numbers":
            if "numbers" not in self.payload:
                raise ValueError(
                    "sum_numbers payload must contain 'numbers'"
                )

            if not isinstance(self.payload["numbers"], list):
                raise ValueError(
                    "'numbers' must be a list"
                )

            # all here uses an expression, then supplies the variable in that expression next, here it checks if all values in numbers is actuall a number
            if not all(
                isinstance(number, (int, float))
                for number in self.payload["numbers"]
            ):
                raise ValueError(
                    "'numbers' must contain only numbers"
                )
        elif self.job_type == "fail_then_succeed":
            if "fail_first_n" not in self.payload:
                raise ValueError (
                    "fail_then_succeed payload must contain 'fail_first_n'"
                )
            if not isinstance(self.payload["fail_first_n"], int):
                raise ValueError(
                    "'fail_first_n' must be a integer"
                )
            if self.payload["fail_first_n"] < 0:
                raise ValueError(
                    "'fail_first_n' must be >= 0"
                )
        elif self.job_type == "process_document":
            if set(self.payload.keys()) != {"document_id"}: # checks the keys specifically instead of seeing if something is merely in it
                raise ValueError("process_document payload must contain only document_id")

            document_id = self.payload["document_id"]
            try:
                UUID(str(document_id)) # UUID tries ot parse string as UUID, if not, vlaue erro and we knw it's not a UUID
            except ValueError:
                raise ValueError("document_id must be a valid UUID")

        return self
