package EcoGrid.service;

import EcoGrid.dao.AlertasOperativaRepository;
import EcoGrid.dto.AlertasOperativaDto;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class AlertasOperativaService {

    private final AlertasOperativaRepository repository;

    public AlertasOperativaService(AlertasOperativaRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<AlertasOperativaDto> listarTodas() {
        return repository.findAllByOrderByIdtiempo_FechoraDesc()
                .stream()
                .map(AlertasOperativaDto::desdeEntidad)
                .toList();
    }
}